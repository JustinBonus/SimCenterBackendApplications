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


# Other custom modules
from hydroUtils import hydroUtils

####################################################################
# OpenFOAM7 solver class
####################################################################
class of7Turbulence():
	"""
	This class includes the methods related to
	turbulence for openfoam7.

	Methods
	--------
		decomptext: Get all the text for the decomposeParDict
	"""

	#############################################################
	def turbtext(self,data):
		'''
		Creates the necessary files for turbulenceDict for openfoam7

		Arguments
		-----------
			data: all the JSON data
		'''

		# Create a utilities object
		hydroutil = hydroUtils()

		# Get the header text for the U-file
		turbtext = self.turbheader()

		# Get the type of turbulence model
		turbmodel = ', '.join(hydroutil.extract_element_from_json(data, ["Events","TurbulenceModel"]))

		if int(turbmodel) == 0:
			turbtext = turbtext + '\nsimulationType\tlaminar;\n'
		elif int(turbmodel) == 1:
			turbtext = turbtext + 'simulationType\tRAS;\n\n'
			turbtext = turbtext + 'RAS\n{\n'
			turbtext = turbtext + '\tRASModel\tkEpsilon;\n'
			turbtext = turbtext + '\tturbulence\ton;\n'
			turbtext = turbtext + '\tprintCoeffs\ton;\n}\n'
		elif int(turbmodel) == 2:
			turbtext = turbtext + 'simulationType\tRAS;\n\n'
			turbtext = turbtext + 'RAS\n{\n'
			turbtext = turbtext + '\tRASModel\tkOmegaSST;\n'
			turbtext = turbtext + '\tturbulence\ton;\n'
			turbtext = turbtext + '\tprintCoeffs\ton;\n}\n'

		return turbtext

	#############################################################
	def turbheader(self):
		'''
		Creates the text for the header

		Variable
		-----------
			header: Header for the turbulence properties-file
		'''

		header = """/*--------------------------*- NHERI SimCenter -*----------------------------*\ 
|	   | H |
|	   | Y | HydroUQ: Water-based Natural Hazards Modeling Application
|======| D | Website: simcenter.designsafe-ci.org/research-tools/hydro-uq
|	   | R | Version: 1.00
|	   | O |
\*---------------------------------------------------------------------------*/ 
FoamFile
{\n\tversion\t2.0;\n\tformat\tascii;\n\tclass\tdictionary;\n\tlocation\t"constant";\n\tobject\tturbulenceProperties;\n}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //\n\n"""

		# Return the header for U file
		return header

