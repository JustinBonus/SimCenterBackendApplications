#  # noqa: INP001, D100
# Copyright (c) 2018 Leland Stanford Junior University
# Copyright (c) 2018 The Regents of the University of California
#
# This file is part of the SimCenter Backend Applications
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# You should have received a copy of the BSD 3-Clause License along with
# this file. If not, see <http://www.opensource.org/licenses/>.
#
# Contributors:
# Kuanshi Zhong
#

import json
import os

import numpy as np
import pandas as pd


def create_wind_scenarios(scenario_info, event_info, stations, data_dir):  # noqa: C901, D103
    # Number of scenarios
    source_num = scenario_info.get('Number', 1)

    # Directly defining earthquake ruptures
    if scenario_info['Generator'] == 'Simulation':
        # Collecting site locations
        lat = []
        lon = []
        for s in stations['Stations']:
            lat.append(s['Latitude'])
            lon.append(s['Longitude'])
        # Station list
        station_list = {'Latitude': lat, 'Longitude': lon}
        # Track data
        try:
            track_file = scenario_info['Storm'].get('Track')
            df = pd.read_csv(  # noqa: PD901
                os.path.join(data_dir, track_file),  # noqa: PTH118
                header=None,
                index_col=None,
            )
            track = {
                'Latitude': df.iloc[:, 0].values.tolist(),  # noqa: PD011
                'Longitude': df.iloc[:, 1].values.tolist(),  # noqa: PD011
            }
        except:  # noqa: E722
            print(  # noqa: T201
                'CreateScenario: error - no storm track provided or file format not accepted.'
            )
        # Save Lat_w.csv
        track_simu_file = scenario_info['Storm'].get('TrackSimu', None)
        if track_simu_file:
            df = pd.read_csv(  # noqa: PD901
                os.path.join(data_dir, track_simu_file),  # noqa: PTH118
                header=None,
                index_col=None,
            )
            #track_simu = df.iloc[:, 0].values.tolist()  # noqa: PD011
            track_simu = {
                'Latitude': df.iloc[:, 0].values.tolist(),  # noqa: PD011
                'Longitude': df.iloc[:, 1].values.tolist(),  # noqa: PD011
            }
        else:
            #track_simu = track['Latitude']
            track_simu = track


        # Reading Terrain info (if provided)
        terrain_file = scenario_info.get('Terrain', None)
        if terrain_file:
            with open(os.path.join(data_dir, terrain_file)) as f:  # noqa: PTH118, PTH123
                terrain_data = json.load(f)
        else:
            terrain_data = []
        # Parsing storm properties
        param = []
        try:
            param.append(scenario_info['Storm']['Landfall']['Latitude'])
            param.append(scenario_info['Storm']['Landfall']['Longitude'])
            param.append(scenario_info['Storm']['Landfall']['LandingAngle'])
            #param.append(scenario_info['Storm']['Landfall']['Pressure'])
            #param.append(scenario_info['Storm']['Landfall']['Speed'])
            #param.append(scenario_info['Storm']['Landfall']['Radius'])
            landfall_prs = 1013.0 - float(scenario_info['Storm']['Landfall']['Pressure']) 
            landfall_spd = float(scenario_info['Storm']['Landfall']['Speed'])* 1.852  # from kts to km/h
            landfall_rad = float(scenario_info['Storm']['Landfall']['Radius'])* 1.852 # from nmile to km
        except:  # noqa: E722
            print('CreateScenario: please provide all needed landfall properties.')  # noqa: T201



        track_simu,dummy,dummy,dummy = interpolate_track(track_simu)
        prs_list, spd_list, rad_list = landfall2track(landfall_prs, landfall_spd, landfall_rad, track_simu)


        # Monte-Carlo
        # del_par = [0, 0, 0] # default
        # Parsing mesh configurations
        mesh_info = [1000.0, scenario_info['Mesh']['DivRad'], 1000000.0]
        mesh_info.extend([0.0, scenario_info['Mesh']['DivDeg'], 360.0])
        # Wind speed measuring height
        measure_height = event_info['IntensityMeasure']['MeasureHeight']
        # Saving results
        scenario_data = dict()  # noqa: C408
        for i in range(source_num):
            scenario_data.update(
                {
                    i: {
                        'Type': 'Wind',
                        'CycloneParam': param,
                        'Pressure': prs_list,
                        'Speed': spd_list,
                        'Radius': rad_list,
                        'StormTrack': track,
                        'StormMesh': mesh_info,
                        'Terrain': terrain_data,
                        'TrackSimu': track_simu,
                        'StationList': station_list,
                        'MeasureHeight': measure_height,
                    }
                }
            )
        # return
        return scenario_data

    # Using the properties of a historical storm to do simulation
    elif scenario_info['Generator'] == 'SimulationHist':  # noqa: RET505
        # Collecting site locations
        lat = []
        lon = []
        for s in stations['Stations']:
            lat.append(s['Latitude'])
            lon.append(s['Longitude'])
        # Station list
        station_list = {'Latitude': lat, 'Longitude': lon}
        # Loading historical storm database
        df_hs = pd.read_csv(
            os.path.join(  # noqa: PTH118
                os.path.dirname(__file__),  # noqa: PTH120
                'database/historical_storm/ibtracs.last3years.list.v04r00.csv',
            ),
            header=[0, 1],
            index_col=None,
        )
        # Storm name and year
        try:
            storm_name = scenario_info['Storm'].get('Name')
            storm_year = scenario_info['Storm'].get('Year')
        except:  # noqa: E722
            print('CreateScenario: error - no storm name or year is provided.')  # noqa: T201
        # Searching the storm
        try:
            df_chs = df_hs[df_hs[('NAME', ' ')] == storm_name]  # noqa: RUF031, RUF100
            df_chs = df_chs[df_chs[('SEASON', 'Year')] == storm_year]  # noqa: RUF031, RUF100
        except:  # noqa: E722
            print('CreateScenario: error - the storm is not found.')  # noqa: T201
        if len(df_chs.values) == 0:
            print('CreateScenario: error - the storm is not found.')  # noqa: T201
            return 1
        # Collecting storm properties
        track_lat = []
        track_lon = []
        for x in df_chs[('USA_LAT', 'degrees_north')].values.tolist():  # noqa: PD011, RUF031, RUF100
            if x != ' ':
                track_lat.append(float(x))  # noqa: PERF401
        for x in df_chs[('USA_LON', 'degrees_east')].values.tolist():  # noqa: PD011, RUF031, RUF100
            if x != ' ':
                track_lon.append(float(x))  # noqa: PERF401
        # If the default option (USA_LAT and USA_LON) is not available, switching to LAT and LON
        if len(track_lat) == 0:
            print(  # noqa: T201
                'CreateScenario: warning - the USA_LAT and USA_LON are not available, switching to LAT and LON.'
            )
            for x in df_chs[('LAT', 'degrees_north')].values.tolist():  # noqa: PD011, RUF031, RUF100
                if x != ' ':
                    track_lat.append(float(x))  # noqa: PERF401
            for x in df_chs[('LON', 'degrees_east')].values.tolist():  # noqa: PD011, RUF031, RUF100
                if x != ' ':
                    track_lon.append(float(x))  # noqa: PERF401
        if len(track_lat) == 0:
            print('CreateScenario: error - no track data is found.')  # noqa: T201
            return 1
        # Saving the track
        track = {'Latitude': track_lat, 'Longitude': track_lon}
        # Reading Terrain info (if provided)
        terrain_file = scenario_info.get('Terrain', None)
        if terrain_file:
            with open(os.path.join(data_dir, terrain_file)) as f:  # noqa: PTH118, PTH123
                terrain_data = json.load(f)
        else:
            terrain_data = []
        # Storm characteristics at the landfall
        dist2land = []
        for x in df_chs[('DIST2LAND', 'km')]:  # noqa: RUF031, RUF100
            if x != ' ':
                dist2land.append(x)  # noqa: PERF401
        if len(track_lat) == 0:
            print('CreateScenario: error - no landing information is found.')  # noqa: T201
            return 1
        if 0 not in dist2land:
            print(  # noqa: T201
                'CreateScenario: warning - no landing fall is found, using the closest location.'
            )
            tmploc = dist2land.index(min(dist2land))
        else:
            tmploc = dist2land.index(
                0
            )  # the first landing point in case the storm sway back and forth
        
        # simulation track
        track_simu_file = scenario_info['Storm'].get('TrackSimu', None)
        if track_simu_file:
            try:
                df = pd.read_csv(  # noqa: PD901
                    os.path.join(data_dir, track_simu_file),  # noqa: PTH118
                    header=None,
                    index_col=None,
                )
                #track_simu = df.iloc[:, 0].values.tolist()  # noqa: PD011

                track_simu = {
                    'Latitude': df.iloc[:, 0].values.tolist(),  # noqa: PD011
                    'Longitude': df.iloc[:, 1].values.tolist(),  # noqa: PD011
                }

            except:  # noqa: E722
                print(  # noqa: T201
                    'CreateScenario: warning - TrackSimu file not found, using the full track.'
                )
                #track_simu = track_lat
                track_simu = track
        else:
            print(  # noqa: T201
                'CreateScenario: warning - no truncation defined, using the full track.'
            )
            # tmp = track_lat
            # track_simu = tmp[max(0, tmploc - 5): len(dist2land) - 1]
            # print(track_simu)
            #track_simu = track_lat
            track_simu = track


        # Reading data
        try:
            landfall_lat = float(df_chs[('USA_LAT', 'degrees_north')].iloc[tmploc])  # noqa: RUF031, RUF100
            landfall_lon = float(df_chs[('USA_LON', 'degrees_east')].iloc[tmploc])  # noqa: RUF031, RUF100
        except:  # noqa: E722
            # If the default option (USA_LAT and USA_LON) is not available, switching to LAT and LON
            landfall_lat = float(df_chs[('LAT', 'degrees_north')].iloc[tmploc])  # noqa: RUF031, RUF100
            landfall_lon = float(df_chs[('LON', 'degrees_east')].iloc[tmploc])  # noqa: RUF031, RUF100
        try:
            landfall_ang = float(df_chs[('STORM_DIR', 'degrees')].iloc[tmploc])  # noqa: RUF031, RUF100
        except:  # noqa: E722
            print('CreateScenario: error - no landing angle is found.')  # noqa: T201
        if landfall_ang > 180.0:  # noqa: PLR2004
            landfall_ang = landfall_ang - 360.0
        # prs_list = (
        #     1013.0
        #     - np.min(
        #         [
        #             float(x)
        #             for x in df_chs[('USA_PRES', 'mb')]  # noqa: PD011, RUF031, RUF100
        #             .iloc[:]
        #             .values.tolist()
        #             if x != ' '
        #         ]
        #     )
        # )

        air_pressure = df_chs[('USA_PRES', 'mb')].iloc[:].values.tolist() 
        prs_list = []
        for x in air_pressure:
            if x == ' ':
                prs_list += [0] # no record == insignificant dp
            else:
                prs_list += [1013.0  - float(x)]


        # prs_list = [1013.0 - float(x) for x in df_chs[('USA_PRES', 'mb')].iloc[:].values.tolist() ]

        # spd_list = (
        #     # float(df_chs[('STORM_SPEED', 'kts')].iloc[tmploc]) * 0.51444  # noqa: RUF031, RUF100 
        #     float(df_chs[('STORM_SPEED', 'kts')].iloc[:]) * 0.00051444  # noqa: RUF031, RUF100  
        # )  # convert knots to km/h // TODO: check if it was intended to be km/s or m/s. If it should be km/s this is correct.

        spd_list = [float(x)* 1.852   for x in df_chs[('STORM_SPEED', 'kts')].iloc[:].values.tolist() ] 

        try:
            # rad_list = (
            #     float(df_chs[('USA_RMW', 'nmile')].iloc[:]) * 1.852  # noqa: RUF031, RUF100   
            # )  # convert nmile to km // sy - from nmile to km is 1.852 not 1.609
            rad_list = [float(x)* 1.852 for x in df_chs[('USA_RMW', 'nmile')].iloc[:].values.tolist() ]

        except:  # noqa: E722
            # No available radius of maximum wind is found
            print('CreateScenario: warning - switching to REUNION_RMW.')  # noqa: T201
            try:
                # If the default option (USA_RMW) is not available, switching to REUNION_RMW
                # rad_list = (
                #     float(df_chs[('REUNION_RMW', 'nmile')].iloc[:]) * 1.852# noqa: RUF031, RUF100  
                # )  # convert nmile to km // sy - from nmile to km is 1.852 not 1.609
                rad_list = [float(x)* 1.852 for x in df_chs[('REUNION_RMW', 'nmile')].iloc[:].values.tolist() ]

            except:  # noqa: E722
                # No available radius of maximum wind is found
                print(  # noqa: T201
                    'CreateScenario: warning - no available radius of maximum wind is found, using a default 50 km.'
                )
                rad_list = 50


        track_simu, prs_list, spd_list, rad_list = interpolate_track(track_simu, prs_list, spd_list, rad_list )


        param = []
        param.append(landfall_lat)
        param.append(landfall_lon)
        param.append(landfall_ang)
        #param.append(prs_list)
        #param.append(spd_list)
        #param.append(rad_list)
        # Monte-Carlo
        # del_par = [0, 0, 0] # default
        # Parsing mesh configurations
        mesh_info = [1000.0, scenario_info['Mesh']['DivRad'], 1000000.0]
        mesh_info.extend([0.0, scenario_info['Mesh']['DivDeg'], 360.0])
        # Wind speed measuring height
        measure_height = event_info['IntensityMeasure']['MeasureHeight']
        # Saving results
        scenario_data = dict()  # noqa: C408
        for i in range(source_num):
            scenario_data.update(
                {
                    i: {
                        'Type': 'Wind',
                        'CycloneParam': param,
                        'Pressure': prs_list,
                        'Speed': spd_list,
                        'Radius': rad_list,
                        'StormTrack': track,
                        'StormMesh': mesh_info,
                        'Terrain': terrain_data,
                        'TrackSimu': track_simu,
                        'StationList': station_list,
                        'MeasureHeight': measure_height,
                    }
                }
            )
        # return
        return scenario_data

    else:
        print('CreateScenario: currently only supporting Simulation generator.')  # noqa: T201, RET503



def interpolate_track(track_simu, prs_list=None, spd_list=None, rad_list=None):  # noqa: C901, D103

    # if maximum of (dlat, dlong) is larger than the threshold value, we will add more intermediate points

    track_lat = track_simu['Latitude']
    track_long = track_simu['Longitude']
    thres = 0.1

    track_lat_new = [track_lat[0]]
    track_long_new = [track_long[0]]

    if prs_list is not None:
        prs_new =  [prs_list[0]]
        spd_new =  [spd_list[0]]
        rad_new =  [rad_list[0]]
    else:
        prs_new, spd_new, rad_new = None, None, None
        
    for nn in range(len(track_lat)-1):
        dlat = (track_lat[nn+1]-track_lat[nn])
        dlon = (track_long[nn+1]-track_long[nn])

        if prs_list is not None:
            dp = (prs_list[nn+1]-prs_list[nn])
            ds = (spd_list[nn+1]-spd_list[nn])
            dr = (rad_list[nn+1]-rad_list[nn])


        npoints = int(max(dlat, dlon)//thres) + 1 # // is same as Ceil: This should be 1 if interval is sufficiently small
        for np in range(npoints):
            track_lat_new += [track_lat[nn] + dlat/npoints*(np+1)]
            track_long_new += [track_long[nn] + dlon/npoints*(np+1)]

            if prs_list is not None:
                prs_new += [prs_list[nn] + dp/npoints*(np+1)]
                spd_new += [spd_list[nn] + ds/npoints*(np+1)]
                rad_new += [rad_list[nn] + dr/npoints*(np+1)]

    track_simu_interpolated = {
                'Latitude': track_lat_new,
                'Longitude': track_long_new
            }       

    return track_simu_interpolated, prs_new, spd_new, rad_new


def landfall2track(landfall_prs, landfall_spd, landfall_rad, track_simu):
    
    # TODO filling model should replace this function
    #print(landfall_prs)
    #print(track_simu)
    prs_list = [landfall_prs] * len(track_simu['Latitude'])
    psd_list = [landfall_spd] * len(track_simu['Latitude'])
    rad_list = [landfall_rad] * len(track_simu['Latitude'])

    return prs_list, psd_list, rad_list, 