import pandas as pd
import numpy as np
import math


file_path = 'FY25_ADC_HS_Data_Updated.xlsx'

data = pd.read_excel(file_path, sheet_name= 'FY25 ADC High School Data Updat')

# {"MISSION ELAPSED TIME (mins)" : [1,2,3,4,5], "Rx(km)[J2000-EARTH]" : [02,334,34,3], "Ry(km)[J2000-EARTH]" : [23,23,2]}

# THE KEY FOR NUMBER TO SATELLITE NAME
KEY = {"WPSA": 1, "DS24": 2, "DS34": 3, "DS54": 4}


def key_to_satellite_name(key):
    for satellite_name, value in KEY.items():
        if value == key:
            return satellite_name
    return None

def generate_kinetic_energy():

    vx = data["Vx(km/s)[J2000-EARTH]"].values
    vy = data["Vy(km/s)[J2000-EARTH]"].values
    vz = data["Vz(km/s)[J2000-EARTH]"].values
    mass = data["MASS (kg)"].values

    velocity_magnitudes = np.sqrt(vx**2 + vy**2 + vz**2)*1000
    
    
    kinetic_energy = 0.5*mass*(velocity_magnitudes**2)


    return kinetic_energy

def generate_Earth_distance():
    rx = data['Rx(km)[J2000-EARTH]'].values
    ry = data['Ry(km)[J2000-EARTH]'].values
    rz = data['Rz(km)[J2000-EARTH]'].values

    magnitude_displacements = np.sqrt(rx**2 + ry**2 + rz**2)
    
    return magnitude_displacements

def generate_velocity_data():

    vx = data["Vx(km/s)[J2000-EARTH]"].values
    vy = data["Vy(km/s)[J2000-EARTH]"].values
    vz = data["Vz(km/s)[J2000-EARTH]"].values

    velocity_magnitudes = np.sqrt(vx**2 + vy**2 + vz**2)

    return velocity_magnitudes

def generate_Moon_distance():

    rx = data['Rx(km)[J2000-EARTH]'].values
    ry = data['Ry(km)[J2000-EARTH]'].values
    rz = data['Rz(km)[J2000-EARTH]'].values

    magnitude_displacements = np.sqrt((rx+373326)**2 + (ry+129357)**2 + (rz+62069)**2)

    return magnitude_displacements


def generate_total_distance():
    rx = data['Rx(km)[J2000-EARTH]'].values
    ry = data['Ry(km)[J2000-EARTH]'].values
    rz = data['Rz(km)[J2000-EARTH]'].values

    total_distance = [0]

    for i in range(1, len(rx)):
        rx_diff = rx[i] - rx[i-1]
        ry_diff = ry[i] - ry[i-1]
        rz_diff = rz[i] - rz[i-1]

        total_distance.append(total_distance[i-1] + np.sqrt(rx_diff**2 + ry_diff**2 + rz_diff**2))
    return total_distance


#------------------------------LINK BUDGET CALCULATIONS--------------------------------


PT = 10
GT = 9
LOSSES = 19.43
NR = 0.55
LAMBDA = 0.136363636
KB = -228.6
TS = 222

def link_budget(satellite_name, satellite_on, satellite_range):
    DR = 0

    if satellite_name == "DS24":
        DR = 34
    if satellite_name == "DS34":
        DR = 34
    if satellite_name == "DS54":
        DR = 34
    if satellite_name == "WPSA":
        DR = 12
    
    exponent = 0.1*(PT + GT - LOSSES +10*np.log10(NR*((np.pi*DR/LAMBDA)**2)) - 20*np.log10((4000*np.pi*satellite_range)/LAMBDA) - KB - 10*np.log10(TS))
        
    bit_rate = satellite_on*((10**(exponent))/1000)

    bit_rate[np.isnan(bit_rate)] = 0

    for i in range(len(bit_rate)):
        if bit_rate[i] > 10000:
            bit_rate[i] = 10000
            
    # print(satellite_name,np.unique(bit_rate))
    
    return bit_rate

def number_connected_satellites():

    number_connected_satellites = []
    satellite_names = ["DS24", "DS34", "DS54", "WPSA"]

    for index in range(len(data["DS24"])):
            connected_satellites = 0
            for satellite in satellite_names:
                if data[satellite][index] > 0:
                    connected_satellites += 1
            number_connected_satellites.append(connected_satellites)

    number_connected_satellites = np.array(number_connected_satellites)
    return number_connected_satellites






#------------------------------Generate Link Budget Data------------------------------------

satellite_names = ["DS24", "DS34", "DS54", "WPSA"]
for satellite in satellite_names:
    satellite_on = data[satellite].values
    satellite_range = 0
    if satellite == "DS24" or satellite == "DS34":
        satellite_range = data["Range " + satellite].values
    else:
        satellite_range = data[satellite + " Range"].values

    link_budget_data = link_budget(satellite, satellite_on, satellite_range)
    data[satellite + " Bit Rate"] = link_budget_data

data["Connected Satellites Count"] = number_connected_satellites()



#------------------------------Sort Satellites Based On Link Budget Function ------------------------------------

def link_budget_sort(link_dict):


    satellite_names = []
    satellite_bitrates = []

    for name, pos in link_dict.items():
        satellite_names.append(name)
        satellite_bitrates.append(pos)
    l = len(link_dict)
    
    while 1 != l:
        l = l - 1
        x = 0
        while x < l:
            if satellite_bitrates[x] < satellite_bitrates[x+1]:
                satellite_bitrates[x], satellite_bitrates[x+1] = satellite_bitrates[x+1], satellite_bitrates[x]
                satellite_names[x], satellite_names[x+1] = satellite_names[x+1], satellite_names[x]
            x = x + 1
    sorted_dict = {}
    i = 0
    for name in satellite_names:
        temp = satellite_bitrates[i]
        sorted_dict[name] = temp
        i = i +1
    return sorted_dict

#------------------------------Sort Satellites Based On ------------------------------------

def switches_sort(index, switches_prioritization):

    current_moment_dict = {"WPSA": data["WPSA_RANGE_LEN"][index], "DS24": data["DS24_RANGE_LEN"][index], "DS34": data["DS34_RANGE_LEN"][index], "DS54": data["DS54_RANGE_LEN"][index]}

    sorted = list(link_budget_sort(current_moment_dict).keys())

    if len(switches_prioritization) == 0:
        return sorted
    
    last_moment = switches_prioritization[-1]
    last_moment_top_connection = key_to_satellite_name(int(last_moment.split(",")[0]))

    if data[last_moment_top_connection][index] == 0:
        return sorted
    else:
        sorted.remove(last_moment_top_connection)
        final_dict = [last_moment_top_connection]
        final_dict = final_dict + sorted
        return final_dict




data['Distance(km)[J2000-EARTH]'] = generate_Earth_distance()
data["Kinetic Energy(J)[J2000-EARTH]"] = generate_kinetic_energy()
data["Velocity Magnitude(km)[J2000-EARTH]"] = generate_velocity_data()
data["Total Distance(km)[J2000-EARTH]"] = generate_total_distance()
data["Moon Distance(km)[J2000-EARTH]"] = generate_Moon_distance()


def mission_status():
    mission_status = []
    time = data["MISSION ELAPSED TIME (min)"].values
    distance_from_earth = data['Distance(km)[J2000-EARTH]'].values
    for i in range(len(time)):
        if time[i] < 1500:
            mission_status.append("Orbiting Earth")
        elif time[i] <= 7600:
            mission_status.append("On the Way To The Moon")
        elif time[i] > 7600 and distance_from_earth[i] > 10000:
            mission_status.append("Returning to Earth")
        elif time[i] > 7600 and distance_from_earth[i] < 10000 and (len(time)- i) > 100:
            mission_status.append("Entry")
        else:
            mission_status.append("Descent and Landing")
    return mission_status

data["Mission Status"] = mission_status()
#------------------------------Sort Satellites Based On Link Budget Function ------------------------------------

link_prioritization = []
for index in range(len(data["WPSA"])):
    order_moment = ""
    sorted_dict = link_budget_sort({"WPSA": data["WPSA Bit Rate"][index], "DS24": data["DS24 Bit Rate"][index], "DS34": data["DS34 Bit Rate"][index], "DS54": data["DS54 Bit Rate"][index]})
    # print(sorted_dict)
    for name, bitrate in sorted_dict.items():
        order_moment = order_moment + "," + str(KEY[name])
    order_moment = order_moment[1:]
    link_prioritization.append(order_moment)
data["Link Budget Prioritization"] = link_prioritization

#------------------------------Sort Satellites Based On Amount of Switches-----------------------------------

switches_prioritization = []

for index in range(len(data["WPSA"])):
    order_moment = ""
    sorted_list = switches_sort(index, switches_prioritization)
    # print(sorted_dict)
    for name in sorted_list:
        order_moment = order_moment + "," + str(KEY[name])
    order_moment = order_moment[1:]
    switches_prioritization.append(order_moment)
data["Switches Prioritization"] = switches_prioritization

#----------------------------------------------------------------------------------------------------------------

data["Connected Satellites Count"] = number_connected_satellites()


data.to_excel(file_path, sheet_name="FY25 ADC High School Data Updat", index = False)

# print(data["Total Distance(km)[J2000-EARTH]"])


