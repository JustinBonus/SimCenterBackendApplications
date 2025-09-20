#!/usr/bin/env python3 # noqa: EXE001, D100
import argparse
import json
import sys
import os
import subprocess
import shutil
import tempfile
import time
import logging
import platform
import threading
import queue
import signal
from typing import Optional

logger = logging.getLogger(__name__)

class FloorForces:  # noqa: D101
    def __init__(self):
        self.X = [0]
        self.Y = [0]
        self.Z = [0]


def directionToDof(direction):  # noqa: N802
    """Converts direction to degree of freedom"""  # noqa: D400, D401
    directionMap = {'X': 1, 'Y': 2, 'Z': 3}  # noqa: N806
    return directionMap[direction]


def addFloorForceToEvent(  # noqa: N802
    timeSeriesArray,  # noqa: N803
    patternsArray,  # noqa: N803
    force,
    direction,
    floor,
    dT,  # noqa: N803
):
    """Add force (one component) time series and pattern in the event file"""  # noqa: D400
    seriesName = 'HydroForceSeries_' + str(floor) + direction  # noqa: N806
    timeSeries = {'name': seriesName, 'dT': dT, 'type': 'Value', 'data': force}  # noqa: N806

    timeSeriesArray.append(timeSeries)
    patternName = 'HydroForcePattern_' + str(floor) + direction  # noqa: N806
    pattern = {
        'name': patternName,
        'timeSeries': seriesName,
        'type': 'HydroFloorLoad',
        'floor': str(floor),
        'dof': directionToDof(direction),
    }

    patternsArray.append(pattern)


def addFloorForceToEvent(patternsArray, force, direction, floor):  # noqa: ARG001, N802, N803, F811
    """Add force (one component) time series and pattern in the event file"""  # noqa: D400
    seriesName = 'HydroForceSeries_' + str(floor) + direction  # noqa: N806
    patternName = 'HydroForcePattern_' + str(floor) + direction  # noqa: N806
    pattern = {
        'name': patternName,
        'timeSeries': seriesName,
        'type': 'HydroFloorLoad',
        'floor': str(floor),
        'dof': directionToDof(direction),
    }

    patternsArray.append(pattern)


def addFloorPressure(pressureArray, floor):  # noqa: N802, N803
    """Add floor pressure in the event file"""  # noqa: D400
    floorPressure = {'story': str(floor), 'pressure': [0.0, 0.0]}  # noqa: N806

    pressureArray.append(floorPressure)


def writeEVENT(forces, eventFilePath):  # noqa: N802, N803
    """This method writes the EVENT.json file"""  # noqa: D400, D401, D404
    timeSeriesArray = []  # noqa: N806, F841
    patternsArray = []  # noqa: N806
    pressureArray = []  # noqa: N806
    hydroEventJson = {  # noqa: N806
        'type': 'Hydro',  # Using HydroUQ
        'subtype': 'MPM',  # Using ClaymoreUW Material Point Method
        # "timeSeries": [], # From GeoClawOpenFOAM
        'pattern': patternsArray,
        'pressure': pressureArray,
        # "dT": deltaT, # From GeoClawOpenFOAM
        'numSteps': len(forces[0].X),
        'units': {'force': 'Newton', 'length': 'Meter', 'time': 'Sec'},
    }

    # Creating the event dictionary that will be used to export the EVENT json file
    eventDict = {'randomVariables': [], 'Events': [hydroEventJson]}  # noqa: N806

    # Adding floor forces
    for floorForces in forces:  # noqa: N806
        floor = forces.index(floorForces) + 1
        addFloorForceToEvent(patternsArray, floorForces.X, 'X', floor)
        addFloorForceToEvent(patternsArray, floorForces.Y, 'Y', floor)
        # addFloorPressure(pressureArray, floor) # From GeoClawOpenFOAM

    with open(eventFilePath, 'w', encoding='utf-8') as eventsFile:  # noqa: PTH123, N806
        json.dump(eventDict, eventsFile)



def GetFloorsCount(BIMFilePath):  # noqa: N802, N803, D103
    with open(BIMFilePath, encoding='utf-8') as BIMFile:  # noqa: PTH123, N806
        bim = json.load(BIMFile)
    return int(bim['GeneralInformation']['stories'])

import sys
import subprocess
import time
import logging
import os
import threading
import queue
import signal

logger = logging.getLogger(__name__)

# Need this because ClaymoreUW sometimes hangs at completion, so this terminates it
def run_claymore_with_finish_monitor(
    exe_path,
    event_json_path,
    finish_marker="Application finished.",
    log_file="claymoreuw_output.txt",
    quiet_success_after=None,  # seconds; if no output for this long, assume success + kill
):
    """
    Run ClaymoreUW with -f <event_json_path>, streaming output.

    Success conditions:
      1) Output contains `finish_marker`  -> terminate and return True
      2) No new output for `quiet_success_after` seconds -> terminate hard and return True
      3) Otherwise, return proc exit code == 0

    All output is mirrored to stdout, to `logging`, and written to `log_file`.
    """
    # Prepare log file
    log_path = os.path.abspath(log_file)
    log_fh = open(log_path, "w", encoding="utf-8")

    # Platform-specific Popen options for better kill behavior
    popen_kwargs = dict(
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    if os.name == "posix":
        popen_kwargs["preexec_fn"] = os.setsid  # start new process group
    else:
        # On Windows, create a new process group (so we can at least try to kill the group)
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    proc = subprocess.Popen([exe_path, "-f", event_json_path], **popen_kwargs)

    # Reader thread to avoid blocking on no-output situations (cross-platform)
    q = queue.Queue()

    def _reader():
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                q.put(line)
        except Exception as e:
            # If something goes wrong, at least record it
            q.put(f"[run_claymore_with_finish_monitor] Reader error: {e}\n")
        finally:
            # Signal EOF with None
            q.put(None)

    t = threading.Thread(target=_reader, daemon=True)
    t.start()

    def _mirror(line: str):
        tagged = f"[ClaymoreUW] {line}"
        # console
        try:
            sys.stdout.write(tagged)
            sys.stdout.flush()
        except Exception:
            pass
        # logger
        try:
            logger.info(tagged.rstrip("\n"))
        except Exception:
            pass
        # file
        log_fh.write(tagged)
        log_fh.flush()

    def _terminate_hard():
        # Try graceful terminate first, then kill; on POSIX also kill the group
        try:
            if proc.poll() is None:
                proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=2)
        except Exception:
            pass

        if proc.poll() is None:
            # POSIX: attempt to kill the whole group
            if os.name == "posix":
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except Exception:
                    pass
                try:
                    proc.wait(timeout=1)
                except Exception:
                    pass
                if proc.poll() is None:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except Exception:
                        pass
            # Finally ensure the process itself is killed
            try:
                proc.kill()
            except Exception:
                pass

    saw_finish = False
    quiet_success = False
    last_output = time.monotonic()  # last time we saw any output

    try:
        while True:
            try:
                # Pull next line with a short timeout so we can check quiet timer
                item = q.get(timeout=0.2)
            except queue.Empty:
                item = None

            now = time.monotonic()

            if item is None:
                # No new line arrived within 0.2s. Check quiet_success timeout.
                if quiet_success_after is not None and (now - last_output) >= quiet_success_after:
                    quiet_success = True
                    _mirror(f"[quiet-success] No output for {quiet_success_after}s; terminating process.\n")
                    _terminate_hard()
                    break

                # If the process already exited and the reader hit EOF and the queue is empty, we can finish.
                if proc.poll() is not None and not t.is_alive() and q.empty():
                    break

                continue

            # Reader signaled EOF explicitly
            if item is None:
                # Already handled above but keep for clarity
                pass

            elif item is not None:
                if item is None:
                    # (kept for completeness)
                    pass
                elif item is not None:
                    # Got a line
                    line = item
                    last_output = now
                    _mirror(line)

                    if finish_marker in line:
                        saw_finish = True
                        _mirror("[finish-marker] Finish marker detected; terminating process.\n")
                        _terminate_hard()
                        break

            # If process has exited and the queue will soon drain, we’ll exit on next loop
            # (handled by checks above)

        # Decide success state
        if saw_finish or quiet_success:
            return True

        # If neither special success happened, fall back to exit code
        rc = proc.wait()
        return rc == 0

    finally:
        try:
            if proc.poll() is None:
                _terminate_hard()
        except Exception:
            pass
        try:
            log_fh.close()
        except Exception:
            pass
        # Let the user know where to find the log
        try:
            print(f"\n[ClaymoreUW] Full output written to {log_path}\n")
        except Exception:
            pass

if __name__ == '__main__':
    """
    Entry point to generate event file using HydroUQ MPM (ClaymoreUW Material Point Method)
    """
    parser = argparse.ArgumentParser(
        description='Get sample EVENT file produced by HydroUQ MPM'
    )
    parser.add_argument('-b', '--filenameAIM', help='BIM File', required=True)
    parser.add_argument('-e', '--filenameEVENT', help='Event File', required=True)
    parser.add_argument(
        '--getRV',
        help='getRV',
        required=False,
        action='store_true',
        default=False,
    )

    arguments, unknowns = parser.parse_known_args()

    if arguments.getRV is True:
        # --- Run ClaymoreUW to generate forces for processing ---
        with open(arguments.filenameAIM, encoding='utf-8') as f:
            aim = json.load(f)

        # pull out first Events entry
        first_event = aim['Events'][0]
        
        # Assuming applications/claymore exists and contains a compiled version of ClaymoreUW (osu_lwf). May only be true on Linux builds.
        if platform.system() == 'Windows':
            claymore_file = 'osu_lwf.exe'
        else:
            claymore_file = 'osu_lwf'
        claymore_exe = os.path.join(
            aim['localAppDir'], 'applications/claymore', claymore_file
        )
        # claymore_exe = os.path.join('/home/justinbonus/SimCenter/claymore/Projects/OSU_LWF', 'osu_lwf') # temp hardcode for testing

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8") as tmpfile:
            json.dump(first_event, tmpfile, ensure_ascii=False)
            tmpfile_path = tmpfile.name
        # tmpfile_path = os.path.join('/home/justinbonus/SimCenter/claymore/Projects/OSU_LWF', 'scene.json') # temp hardcode for testing
        
        # Copy any csv files up one folder
        # src_dir is the current directory of the filenameAIM and all resource files in templatedir
        # dst_dir is the parent directory of this script
        src_dir = '.'
        dst_dir = '..'
        print(f"Copying .csv and other files from {src_dir} to {dst_dir}")  # noqa: T201
        for file_name in os.listdir(src_dir):
            if file_name.endswith('.csv') or file_name.endswith('.bgeo') or file_name.endswith('.geo') or file_name.endswith('.txt') or file_name.endswith('.obj') or file_name.endswith('.stl') or file_name.endswith('.sdf'):
                full_file_name = os.path.join(src_dir, file_name)
                if os.path.isfile(full_file_name):
                    try:
                        shutil.copy(full_file_name, dst_dir)
                    except Exception as e:
                        print(f"Warning: Could not copy {full_file_name} to {dst_dir}: {e}")  # noqa: T201
        
        # Since ClaymoreUW sometimes hangs at the end, we use a timeout [seconds] to kill it if it exceeds this limit without outputting anything to stdout. 
        # This is considered a successful run. Tune as needed.
        if 'timeout' in first_event:
            timeout = first_event['timeout']
        else:
            timeout = 60
        
        ok = run_claymore_with_finish_monitor(
            claymore_exe,
            tmpfile_path,
            finish_marker="Application finished.",
            log_file="claymoreuw_output.txt",
            quiet_success_after=timeout,       # tune as you like
            # env_overrides={"CUDA_LAUNCH_BLOCKING": "1"},  # optional
        )
        if not ok:
            raise RuntimeError("ClaymoreUW did not complete successfully.")



        # # Write first Events object to a temp file (close it so ClaymoreUW can read it on Windows)
        # tmpfile_path = None
        # try:
        #     with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8") as tmpfile:
        #         json.dump(first_event, tmpfile, ensure_ascii=False)
        #         tmpfile_path = tmpfile.name
        #     tmpfile_path = os.path.join('/home/justinbonus/SimCenter/claymore/Projects/OSU_LWF', 'scene.json') # temp hardcode for testing
        #     ok = run_claymore_with_finish_monitor(claymore_exe, tmpfile_path)
        #     if not ok:
        #         raise RuntimeError("ClaymoreUW did not complete successfully (no finish marker and nonzero exit code).")

        # finally:
        #     print('Cleaning up temporary file:', tmpfile_path)  # noqa: T201
        #     if tmpfile_path and os.path.exists(tmpfile_path):
        #         try:
        #             os.remove(tmpfile_path)
        #         except OSError:
        #             pass
        
        
        # # --- Continue with force processing ---
        # floorsCount = GetFloorsCount(arguments.filenameAIM)  # noqa: N816
        # forces = []
        # for _ in range(floorsCount):
        #     forces.append(FloorForces())
        # writeEVENT(forces, arguments.filenameEVENT)
        
        # --- Run GetEventFromMPM.py to process forces into EVENT.json ---
        this_dir = os.path.dirname(os.path.abspath(__file__))
        getevent_path = os.path.join(this_dir, "GetEventFromMPM.py")

        result = subprocess.run(
            [
                sys.executable,
                getevent_path,
                "-c", ".",
                "-b", arguments.filenameAIM
            ], 
            stdout=subprocess.PIPE,
            check=False
        )

        # Copy EVENT.json to EVENT.json.sc
        event_json_path = os.path.join(this_dir, "EVENT.json")
        event_json_sc_path = os.path.join(this_dir, "EVENT.json.sc")
        if os.path.exists(event_json_path):
            try:
                import shutil
                shutil.copyfile(event_json_path, event_json_sc_path)
            except Exception as e:
                print(f"Warning: Could not copy EVENT.json to EVENT.json.sc: {e}")  # noqa: T201
        else:
            print(f"Warning: EVENT.json not found at expected location: {event_json_path}")  # noqa: T201
        

        # cmd = [sys.executable, getevent_path,
        #        "-c", ".", "-b", arguments.filenameAIM]

        # print(f"[Launcher] Running GetEventFromMPM.py: {' '.join(cmd)}")
        # result = subprocess.run(cmd, check=False)

        # if result.returncode != 0:
        #     raise RuntimeError(f"GetEventFromMPM.py failed with exit code {result.returncode}")