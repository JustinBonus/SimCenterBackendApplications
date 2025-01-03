"""authors: Mukesh Kumar Ramancha, Maitreya Manoj Kurumbhati, Prof. J.P. Conte, Aakash Bangalore Satish*
affiliation: University of California, San Diego, *SimCenter, University of California, Berkeley

"""  # noqa: INP001, D205, D400

# ======================================================================================================================
import json
import shlex
import sys
import traceback
from pathlib import Path

path_to_common_uq = Path(__file__).parent.parent / 'common'
sys.path.append(str(path_to_common_uq))


# ======================================================================================================================
def main(input_args):  # noqa: D103
    # # Initialize analysis
    # path_to_UCSD_UQ_directory = Path(input_args[2]).resolve().parent
    # path_to_working_directory = Path(input_args[3]).resolve()
    # path_to_template_directory = Path(input_args[4]).resolve()
    # run_type = input_args[5]  # either "runningLocal" or "runningRemote"
    # driver_file_name = input_args[6]
    # input_file_name = input_args[7]

    # Initialize analysis
    path_to_UCSD_UQ_directory = Path(input_args[0]).resolve().parent  # noqa: N806, F841
    path_to_working_directory = Path(input_args[1]).resolve()
    path_to_template_directory = Path(input_args[2]).resolve()
    run_type = input_args[3]  # either "runningLocal" or "runningRemote"
    driver_file_name = input_args[4]
    input_file_name = input_args[5]

    Path('dakotaTab.out').unlink(missing_ok=True)
    Path('dakotaTabPrior.out').unlink(missing_ok=True)

    input_file_full_path = path_to_template_directory / input_file_name

    with open(input_file_full_path, encoding='utf-8') as f:  # noqa: PTH123
        inputs = json.load(f)

    uq_inputs = inputs['UQ']
    if uq_inputs['uqType'] == 'Metropolis Within Gibbs Sampler':
        import mainscript_hierarchical_bayesian

        main_function = mainscript_hierarchical_bayesian.main
    else:
        import mainscript_tmcmc

        main_function = mainscript_tmcmc.main

    command = (
        f'"{path_to_working_directory}" "{path_to_template_directory}" '
        f'{run_type} "{driver_file_name}" "{input_file_full_path}"'
    )
    command_list = shlex.split(command)

    # Check if 'UCSD_UQ.err' exists, and create it if not
    err_file = path_to_working_directory / 'UCSD_UQ.err'

    if not err_file.exists():
        err_file.touch()  # Create the file

    # Try running the main_function and catch any exceptions
    try:
        main_function(command_list)
    except Exception:  # noqa: BLE001
        # Write the exception message to the .err file
        with err_file.open('a') as f:
            f.write('ERROR: An exception occurred:\n')
            f.write(f'{traceback.format_exc()}\n')


# ======================================================================================================================

if __name__ == '__main__':
    input_args = sys.argv
    main(input_args)

# ======================================================================================================================
