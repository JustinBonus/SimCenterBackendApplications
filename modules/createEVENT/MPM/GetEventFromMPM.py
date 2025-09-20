from __future__ import print_function
import os, sys
import re
import json
import argparse
import numpy

class FloorForces:
    def __init__(self):
        self.X = [0]
        self.Y = [0]
        self.Z = [0]
    
def validateCaseDirectoryStructure(caseDir):
    """
    This method validates that the provided case directory is valid and contains the 0, constant and system directory
    It also checks that system directory contains the controlDict
    """
    if not os.path.isdir(caseDir):
        return False
    
    caseDirList = os.listdir(caseDir)
    # necessaryDirs = ["0", "constant", "system", "postProcessing"]
    # if any(not aDir in caseDirList for aDir in necessaryDirs):
    #     return False

    # controlDictPath = os.path.join(caseDir, "system/controlDict")
    # if not os.path.exists(controlDictPath):
    #     return False
    
    return True

# def parseForceComponents(forceArray):
#     """
#     This method takes the MPM force array and parse into components x,y,z
#     """
#     components = forceArray.strip('()').split()
    
#     x = float(components[0])
#     y = float(components[1])
#     z = float(components[2])
#     return [x, y, z]

def ReadMPMForces(buildingForcesPath, floorsCount, startTime, lengthScale, velocityScale):
    """
    This method will read the forces from the output files in the MPM case output (post processing). 
    It will scale dT and forces using the 2 scale factors: dT *= velocityScale/lengthScale; force *= lengthScale/(velocityScale*velocityScale)

    The scaling is also changed from model-scale to full-scale instead of the other way around
    """
    
    deltaT = 1.0 / 120.0
    forces = []
            
    timeFactor = 1.0/(lengthScale/velocityScale)
    forceFactor = 1.0/(lengthScale*velocityScale)**2.0
    
    for k in range(floorsCount):
        forces.append(FloorForces())
        
        num_gpu = 4
        scalarForceOne = []
        scalarForceTwo = []
        scalarForceThree = []
        scalarForceFour = [] 
        for j in range(num_gpu):
            
            forceFile = "gridTarget[" + str(k) + "]_dev[" + str(j) + "].csv"
            buildingForcesFile = os.path.join(buildingForcesPath, forceFile)
            
            # Check if the file exists
            if not os.path.exists(buildingForcesFile):
                print("File not found: ", buildingForcesFile)
                continue
            
            timeCount = 0
            with open(buildingForcesFile, 'r') as forcesFile:
                forceLines = forcesFile.readlines()
                line_num = 0
                for line in forceLines:
                    # skip the first line header
                    if line_num == 0: 
                        line_num += 1
                        continue 
                            
                    if line.startswith("#"):
                        line_num += 1
                        continue
                    
                    # SPLIT BY COMMAs
                    line = line.replace(",", " ")
                    

                    time = float(line.split()[0]) # This splits the line by spaces and takes the first element as time
                    timeCount += 1
                    
                    # if timeCount==1:
                    #     deltaT = time

                    # if timeCount==2:
                    #     deltaT = time - deltaT
                        
                    
                    if time >= startTime:
                        if j == 0:
                            scalarForceOne.append(float(line.split()[1]))
                        elif j == 1:
                            scalarForceTwo.append(float(line.split()[1]))
                        elif j == 2:
                            scalarForceThree.append(float(line.split()[1]))
                        else:
                            scalarForceFour.append(float(line.split()[1]))
                        # scalarForce += float(line.split()[1])
                        
                    line_num += 1
                                        
                        # detectedForces = re.findall(forcePattern, line)
        
        # Sum the forces from the (upto) 4 GPUs
        
        for i in range(len(scalarForceOne)):
            sumForce = 0.0
            if (i < len(scalarForceOne)):
                sumForce += scalarForceOne[i]
            if (i < len(scalarForceTwo)):
                sumForce += scalarForceTwo[i]
            if (i < len(scalarForceThree)):
                sumForce += scalarForceThree[i]
            if (i < len(scalarForceFour)):
                sumForce += scalarForceFour[i]
            
            # append the force to the forces array
            forces[k].X.append((sumForce)*forceFactor)
            forces[k].Y.append((0.0)*forceFactor)
            forces[k].Z.append((0.0)*forceFactor)
    
    # # Add a small force to allow for EDP calculation when forces are zero on a load cell
    # for k in range(floorsCount+1):
    #     small_force = 1e-6 # small force
    #     forces[k].X.append(small_force)
    #     forces[k].Y.append(small_force)
    #     forces[k].Z.append(small_force)

    deltaT = deltaT*timeFactor
    
    return [deltaT, forces]

def directionToDof(direction):
    """
    Converts direction to degree of freedom
    """
    directionMap = {
        "X": 1,
        "Y": 2,
        "Z": 3
    }

    return directionMap[direction]


def addFloorForceToEvent(timeSeriesArray, patternsArray, force, direction, floor, dT):
    """
    Add force (one component) time series and pattern in the event file
    """
    seriesName = "WindForceSeries_" + str(floor) + direction
    timeSeries = {
                "name": seriesName,
                "dT": dT,
                "numSteps": len(force),
                "type": "Value",
                "data": force
            }
    
    timeSeriesArray.append(timeSeries)
    
    patternName = "WindForcePattern_" + str(floor) + direction
    pattern = {
        "name": patternName,
        "timeSeries": seriesName,
        "type": "WindFloorLoad",
        "floor": str(floor),
        "dof": directionToDof(direction)
    }

    patternsArray.append(pattern)

def addFloorPressure(pressureArray, floor):
    """
    Add floor pressure in the event file
    """
    floorPressure = {
        "story":str(floor),
        "pressure":[0.0, 0.0]
    }

    pressureArray.append(floorPressure)


def writeEVENT(forces, deltaT):
    """
    This method writes the EVENT.json file
    """
    timeSeriesArray = []
    patternsArray = []
    pressureArray = []
    
    windEventJson = {
        "type" : "Wind",
        "subtype": "MPM",
        "timeSeries": timeSeriesArray,
        "pattern": patternsArray,
        "pressure": pressureArray,
        "dT": deltaT,
        "numSteps": len(forces[0].X),
        "units": {
            "force": "Newton",
            "length": "Meter",
            "time": "Sec"
        }
    }

    #Creating the event dictionary that will be used to export the EVENT json file
    eventDict = {"randomVariables":[], "Events": [windEventJson]}

    #Adding floor forces
    for floorForces in forces:
        floor = forces.index(floorForces) + 1
        addFloorForceToEvent(timeSeriesArray, patternsArray, floorForces.X, "X", floor, deltaT)
        addFloorForceToEvent(timeSeriesArray, patternsArray, floorForces.Y, "Y", floor, deltaT)
        addFloorPressure(pressureArray, floor)

    with open("EVENT.json", "w") as eventsFile:
        json.dump(eventDict, eventsFile)


def GetMPMEvent(caseDir, forcesOutputName, floorsCount, startTime, lengthScale, velocityScale):
    """
    Reads MPM output and generate an EVENT file for the building
    """
    if not validateCaseDirectoryStructure(caseDir):
        print("Invalid MPM Case Directory!")
        sys.exit(-1)
        


    if floorsCount == 1:        
        # buildingForcesPath = os.path.join(caseDir, "forces.dat")
        buildingForcesPath = caseDir
    else:
        buildingForcesPath = caseDir
        # buildingForcesPath = os.path.join(caseDir, "gridTarget[]", forcesOutputName, "0", "forces_bins.dat")
        
    [deltaT, forces] = ReadMPMForces(buildingForcesPath, floorsCount, startTime, lengthScale, velocityScale)

    # Write the EVENT file
    writeEVENT(forces, deltaT)

    print("MPM event is written to EVENT.json")

def ReadBIM(BIMFilePath):
    with open(BIMFilePath,'r') as BIMFile:
        bim = json.load(BIMFile)

    eventType = bim["Applications"]["Events"][0]["Application"]
    forcesOutputName = 'buildingsForces'

    if eventType == "DigitalWindTunnel":
        return [forcesOutputName, int(bim["GeneralInformation"]["stories"]), float(bim["Events"][0]["sim"]["start"]), 1.0, 1.0]
    elif eventType == "IsolatedBuildingCFD" or eventType == "SurroundedBuildingCFD":
        nStories = int(bim["GeneralInformation"]["stories"])
        gScale = 1.0/float(bim["Events"][0]["GeometricData"]["geometricScale"])
        vScale = 1.0/float(bim["Events"][0]["windCharacteristics"]["velocityScale"])
        startTime = 0.05*float(bim["Events"][0]["numericalSetup"]["duration"]) #Discard the first 5% of the simulation
        forcesOutputName = 'storyForces'
        return [forcesOutputName, nStories, startTime, gScale, vScale]
    elif eventType == "MPM":
        return [forcesOutputName, int(bim["GeneralInformation"]["stories"]), float(0.0), float(1.0), float(1.0)]
    else:
        if "LengthScale" in bim["Events"][0]:
            return [forcesOutputName, int(bim["GeneralInformation"]["stories"]), float(bim["Events"][0]["start"]), float(bim["Events"][0]["LengthScale"]), float(bim["Events"][0]["VelocityScale"])]
        else:
            return [forcesOutputName, int(bim["GeneralInformation"]["stories"]), float(bim["Events"][0]["start"]), 1.0, 1.0]
        

if __name__ == "__main__":
    """
    Entry point to read the forces from MPM case and use it for the EVENT
    """
    #CLI parser
    parser = argparse.ArgumentParser(description="Get EVENT file from MPM output")
    parser.add_argument('-c', '--case', help="MPM case directory", required=True)
    parser.add_argument('-b', '--bim', help= "path to BIM file", required=False)

    #parsing arguments
    arguments, unknowns = parser.parse_known_args()

    [forcesOutputName, floors, startTime, lengthScale, velocityScale] = ReadBIM(arguments.bim)

    GetMPMEvent(arguments.case, forcesOutputName, floors, startTime, lengthScale, velocityScale)
        
