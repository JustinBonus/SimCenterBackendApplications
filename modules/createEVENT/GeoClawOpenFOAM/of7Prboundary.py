####################################################################
# LICENSING INFORMATION
####################################################################
"""
	LICENSE INFORMATION:
	
	Copyright (c) 2020-2030, The Regents of the University of California (Regents).

	All rights reserved.

	Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

	1. Redistributions of source code must retain the above copyright notice, this 
		list of conditions and the following disclaimer.
	2. Redistributions in binary form must reproduce the above copyright notice,
		this list of conditions and the following disclaimer in the documentation
		and/or other materials provided with the distribution.

	THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

	The views and conclusions contained in the software and documentation are those of the authors and should not be interpreted as representing official policies, either expressed or implied, of the FreeBSD Project.

	REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED "AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
	
"""
####################################################################
# AUTHOR INFORMATION
####################################################################
# 2020 - 2021: Ajay B Harish (ajaybh@berkeley.edu)

####################################################################
# Import all necessary modules
####################################################################
# Standard python modules
import os

# Other custom modules
from hydroUtils import hydroUtils

####################################################################
# OpenFOAM7 solver class
####################################################################
class of7Prboundary():
	"""
	This class includes the methods related to
	pressure boundary conditions for openfoam7.

	Methods
	--------
		Prtext: Get all the text for the p_rgh-file
	"""

	#############################################################
	def Prtext(self,data,patches):
		'''
		Creates the necessary text for pressure bc for openfoam7

		Arguments
		-----------
			data: all the JSON data
		'''

		# Create a utilities object
		hydroutil = hydroUtils()

		# Get the header text for the U-file
		prtext = self.Prheader()

		# Start the outside 
		prtext = prtext + "boundaryField\n{\n"

		# Loop over all patches
		for patchname in patches:
			prtext = prtext + "\t" + patchname + "\n"
			patch = hydroutil.extract_element_from_json(data, ["Events","PressureType_" + patchname])
			if patch == [None]:
				prtype = -1
			else:
				prtype = ', '.join(hydroutil.extract_element_from_json(data, ["Events","PressureType_" + patchname]))
			prtext = prtext + self.Prpatchtext(data,prtype,patchname)

		# Check for building and other building
		prtext = prtext + '\tBuilding\n'
		prtext = prtext + self.Prpatchtext(data,'201','Building')
		prtext = prtext + '\tOtherBuilding\n'
		prtext = prtext + self.Prpatchtext(data,'201','OtherBuilding')

		# Close the outside
		prtext = prtext + "}\n\n"
		
		# Return the text for velocity BC
		return prtext
	
	#############################################################
	def Prheader(self):
		'''
		Creates the text for the header for pressure file

		Variable
		-----------
			header: Header for the p_rgh-file
		'''

		header = """/*--------------------------*- NHERI SimCenter -*----------------------------*\ 
|	   | H |
|	   | Y | HydroUQ: Water-based Natural Hazards Modeling Application
|======| D | Website: simcenter.designsafe-ci.org/research-tools/hydro-uq
|	   | R | Version: 1.00
|	   | O |
\*---------------------------------------------------------------------------*/ 
FoamFile
{\n\tversion\t2.0;\n\tformat\tascii;\n\tclass\tvolScalarField;\n\tlocation\t"0";\n\tobject\tp_rgh;\n}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n\n"""

		header = header + "dimensions\t[1 -1 -2 0 0 0 0];\n\n"
		header = header + "internalField\tuniform\t0;\n\n"
		
		# Return the header for U file
		return header

	#############################################################
	def Prpatchtext(self,data,Prtype,patchname):
		'''
		Creates the text the pressure boundary condition

		Arguments
		-----------
			Prtype: Type of velocity b.c
			patchname: Name of the patch

		Variable
		-----------
			Prtext: Text for the particular patch
		'''

		# Create a utilities object
		hydroutil = hydroUtils()

		# Inlet types
		# For each type, get the text
		if int(Prtype) == 0:
			# Default for velocity type
			# inlet = fixedFluxPressure
			# wall/outlet = zeroGradient
			# Empty = Empty
			Upatch = hydroutil.extract_element_from_json(data, ["Events","VelocityType_" + patchname])
			if Upatch == [None]:
				Utype = -1
			else:
				Utype = ', '.join(hydroutil.extract_element_from_json(data, ["Events","VelocityType_" + patchname]))

			if (int(Utype) > 100) and (int(Utype) < 200):
				Prtype2 = "102"
			elif (int(Utype) > 200) and (int(Utype) < 300):
				Prtype2 = "202"
			elif int(Utype) > 300:
				Prtype2 = "201"
			else:
				Prtype2 = "-1"
		else:
			Prtype2 = Prtype

		# Test for different pressure types
		if int(Prtype2) == 101:
			# fixedValue
			# Get the pressure values
			pres = hydroutil.extract_element_from_json(data, ["Events","Pressure_"+patchname])
			if pres == [None]:
				pr = 0.0
			else:
				presvals = ', '.join(hydroutil.extract_element_from_json(data, ["Events","Pressure_"+patchname]))
				pr = float(presvals)
			# Get the text
			Prtext = "\t{\n\t\t"
			Prtext = Prtext + "type\tfixedValue;\n\t\t"
			Prtext = Prtext + "value\t" + str(pr) + ";\n"
			Prtext = Prtext + "\t}\n"
		elif int(Prtype2) == 102:
			# fixedFluxPressure
			Prtext = "\t{\n\t\t"
			Prtext = Prtext + "type\tfixedFluxPressure;\n\t\t"
			Prtext = Prtext + "value\tuniform 0;\n\t}\n"
		elif int(Prtype2) == 201:
			# Outlet zero gradient
			Prtext = "\t{\n\t\t"
			Prtext = Prtext + "type\tzeroGradient;\n\t}\n"
		elif int(Prtype2) == 202:
			Prtext = "\t{\n\t\t"
			Prtext = Prtext + "type\tfixedValue;\n\t\t"
			Prtext = Prtext + "value\t0;\n"
			Prtext = Prtext + "\t}\n"
		else:
			# Default: Empty
			Prtext = "\t{\n\t\t"
			Prtext = Prtext + "type\tempty;\n\t}\n"
		
		# Return the header for U file
		return Prtext