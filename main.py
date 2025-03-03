import sys
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, 
                             QHBoxLayout, QPushButton, QSlider, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QCheckBox, QDialog, QVBoxLayout, QLabel, QPushButton)
from PyQt5.QtCore import pyqtSignal, QObject
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import mplcursors
from matplotlib import animation
from matplotlib import pyplot
from PyQt5.QtGui import QFont, QColor
import emoji
from datetime import datetime, timedelta





#Load flight path data
file_path = "FY25_ADC_HS_Data_Updated.xlsx"
data = pd.read_excel(file_path)
times = data['MISSION ELAPSED TIME (min)']
distances = data['Distance(km)[J2000-EARTH]']
velocities = data['Velocity Magnitude(km)[J2000-EARTH]']

GLOBAL_INDEX = 0

KEY = {"WPSA": 1, "DS24": 2, "DS34": 3, "DS54": 4}


def add_S(satellite_name):
    if satellite_name[0] != "D":
        return satellite_name[0:2] + "S" + satellite_name[2:]

def key_to_satellite_name(key):
    for satellite_name, value in KEY.items():
        if value == key:
            return satellite_name
    return None

def time_adder(minutes):

    start = "2025-09-01 15:25:47"
    format = "%Y-%m-%d %H:%M:%S"

    start_time = datetime.strptime(start, format)

    new_time = start_time + timedelta(minutes=minutes)

    return str(new_time)

def mission_status_color(index, COLOR_ON):
    if COLOR_ON == False:
        return "black"
    if data["Mission Status"][index] == "Orbiting Earth":
        return "green"
    elif data["Mission Status"][index] == "On the Way To The Moon":
        return "purple"
    elif data["Mission Status"][index] == "Returning to Earth":
        return "brown"
    elif data["Mission Status"][index] == "Entry":
        return "orange"
    elif data["Mission Status"][index] == "Descent and Landing":
        return "pink"
    else:
        return "black"

def update_label_color( label, current_value, previous_value, COLOR_ON):
    if COLOR_ON == False:
        label.setStyleSheet("font-size: 20px; color: black;")
        return
    if current_value > previous_value:
        label.setStyleSheet("font-size: 20px;color: green;")
    elif current_value < previous_value:
        label.setStyleSheet("font-size: 20px;color: red;")
    else:
        label.setStyleSheet("font-size: 20px; color: black;")   


class Flight_Sim_Visual(FigureCanvas):
    index_hovered = pyqtSignal(int)  #

    def __init__(self, p_vec, widgets,velocity_canvas):
        self.figure = Figure()
        self.flightpath = self.figure.add_subplot(111, projection='3d')
        super().__init__(self.figure)
        self.rx = p_vec[0]
        self.ry = p_vec[1]
        self.rz = p_vec[2]
        self.N=2000
        self.frames = range(self.N+1)
        MAX_points = len(self.rx)
        self.dist = 0
        self.itrvl=MAX_points/self.N
        self.ani = None        
        self.plot_static_path()

    def plot_static_path(self):
        if(self.ani != None):
            self.ani.pause()        
        self.figure.clear();
        self.flightpath = self.figure.add_subplot(111, projection='3d')
        scatter_plot = self.flightpath.scatter(self.rx, self.ry, self.rz, color='black', s=2)
        self.flightpath.set_xlabel('X (km)')
        self.flightpath.set_ylabel('Y (km)')
        self.flightpath.set_zlabel('Z (km)')
        #Taken from online forum, enables us to send out the index of the point being hovered
        cursor = mplcursors.cursor(scatter_plot, hover=True)
        cursor.connect("add", lambda sel: self.on_hover(sel))


        #-------------------------------------------EARTH-------------------------------------------


        u = np.linspace(0, 2 * np.pi, 100)
        v = np.linspace(0, np.pi, 100)

        ex = 6378 * np.outer(np.cos(u), np.sin(v))
        ey = 6378 * np.outer(np.sin(u), np.sin(v))
        ez = 6378 * np.outer(np.ones(np.size(u)), np.cos(v))

        # Plot the surface
        self.flightpath.plot_surface(ex, ey, ez, color='blue', alpha=0.6)
        

        #-------------------------------------------MOON-------------------------------------------

        # center the moon at the (-339409,-112769,-58248) position
        
        u = np.linspace(0, 2 * np.pi, 100)
        v = np.linspace(0, np.pi, 100)

        mx = 1737.4 * np.outer(np.cos(u), np.sin(v)) - 373326
        my = 1737.4 * np.outer(np.sin(u), np.sin(v)) - 129357
        mz = 1737.4 * np.outer(np.ones(np.size(u)), np.cos(v)) - 62069

        # Plot the surface
        self.flightpath.plot_surface(mx, my, mz, color='grey', alpha=0.6)
        
        #--------------------------------------------------------------------------------------



    def play_flight_animation(self, widgets, velocity_canvas, the_UI):
        self.figure.clear();
        self.flightpath = self.figure.add_subplot(111, projection='3d')
        line,= self.flightpath.plot([], [], [], color='red', alpha=0.5)       
        graph = line
        self.flightpath.set_xlabel('X (km)')
        self.flightpath.set_ylabel('Y (km)')
        self.flightpath.set_zlabel('Z (km)')
        if(self.ani == None):
            self.ani = animation.FuncAnimation(self.figure, self.update_path, self.frames, #self.N+2, 
                                               fargs=(self.rx, self.ry, self.rz, graph, widgets, velocity_canvas, the_UI), 
                                               interval=5, blit=False, repeat=True)                 
        self.ani.resume()
        
    def on_hover(self, sel):

        index = sel.index
        print(str(round(times[index],2)), index)
        # sel.annotation.set_text(
        #     "Time:" +str(round(times[index],2))+ " mins\n"
        #     +"Position: " + str(round(self.rx[index],2)) + "," + str(round(self.ry[index],2)) + ","+ str(round(self.rz[index],2)) +"\n"
        #     +"Distance from Earth: " + str(round(distances[index],2)) + " km\n"
        #     +"Velocity: "+str(round(velocities[index],2))+" km/s"
        # )
        self.index_hovered.emit(index)  #make the index at that moment global in a sense

    def update_path(self,num,x,y,z,graph, widgets, velocity_canvas, the_UI):        
        dist = int(self.itrvl*num)        
        self.flightpath.plot(x[:dist], y[ :dist], z[ :dist], color='black', alpha=0.5)

        prev_dist = dist - 1
        if dist == 0:
            prev_dist = 0

        the_UI.update_mission_metrics(dist)

        if num%1 == 0:
            velocity_canvas.update_velocity_vector(dist)
            velocity_canvas.draw()
        GLOBAL_INDEX = dist
        the_UI.update_satellite_link_table(dist)
        # graph.set_data(x[:dist], y[:dist])
        # graph.set_3d_properties(z[:dist])    
    
    def pause_flight_animation(self):
        self.ani.pause()
    
    def restart_flight_animation(self, widgets, velocity_canvas, the_UI):
        self.ani.pause()
        self.ani.new_frame_seq()
        self.ani = None

        widgets[0].setText("Time: 0 mins")
        widgets[1].setText("Distance From Earth: 0 km")
        widgets[2].setText("Velocity: 0 km/s")
        widgets[3].setText("Position Vector: <0, 0, 0> km")
        
        for widget in widgets:
            widget.setStyleSheet("font-size: 20px; color: black;")
        
        velocity_canvas.update_velocity_vector(0)
        velocity_canvas.draw()
        
        the_UI.update_satellite_link_table(0)
        self.play_flight_animation(widgets, velocity_canvas, the_UI)

    def add_moon_earth(self):

        u = np.linspace(0, 2 * np.pi, 100)
        v = np.linspace(0, np.pi, 100)
        ex = 6378 * np.outer(np.cos(u), np.sin(v))
        ey = 6378 * np.outer(np.sin(u), np.sin(v))
        ez = 6378 * np.outer(np.ones(np.size(u)), np.cos(v))
        self.flightpath.plot_surface(ex, ey, ez, color='blue', alpha=0.6)


        mx = 1737.4 * np.outer(np.cos(u), np.sin(v)) - 373326
        my = 1737.4 * np.outer(np.sin(u), np.sin(v)) - 129357
        mz = 1737.4 * np.outer(np.ones(np.size(u)), np.cos(v)) - 62069
        self.flightpath.plot_surface(mx, my, mz, color='grey', alpha=0.6)
    
    def remove_moon_earth(self, state_widgets, velocity_canvas, the_UI):
        self.flightpath.clear()
        self.play_flight_animation(state_widgets,velocity_canvas, the_UI)

class Velocity_visual(FigureCanvas):
    def __init__(self, vv_data):
        self.figure = Figure()
        self.velocity_visual = self.figure.add_subplot(111, projection='3d')
        super().__init__(self.figure)

        self.vx = vv_data[0]
        self.vy = vv_data[1]
        self.vz = vv_data[2]
        self.plot_velocity()

    def plot_velocity(self):
        """Plot the static velocity vector."""
        self.velocity_visual.quiver(0, 0, 0, self.vx[0], self.vy[0], self.vz[0], color='red', length=1.0)
        self.velocity_visual.set_xlim([-2, 2])
        self.velocity_visual.set_ylim([-2, 2])
        self.velocity_visual.set_zlim([-2, 2])
        self.velocity_visual.set_title("Velocity Vector")
        self.velocity_visual.set_xlabel("X (km/s)")
        self.velocity_visual.set_ylabel("Y (km/s)")
        self.velocity_visual.set_zlabel("Z (km/s)")

    def update_velocity_vector(self, index):
        """Update the velocity vector displayed in the right-side panel."""
        # Clear the velocity canvas for the new plot
        #self.velocity_visual.figure.clear()        
        #vv_visualization = self.velocity_visual.figure.add_subplot(111, projection='3d')
        vv_visualization = self.velocity_visual;
        vv_visualization.clear()
        vv_visualization.scatter(0, 0, 0, c='blue', marker='*', s=100, label='Artemis II Spacecraft')
        # Plot the new velocity vector
        vv_visualization.set_title(" Resultant Velocity Vector")
        vv_visualization.set_xlabel("X (km/s)")
        vv_visualization.set_ylabel("Y (km/s)")
        vv_visualization.set_zlabel("Z (km/s)")
        vv_visualization.set_xlim([-2, 2])
        vv_visualization.set_ylim([-2, 2])
        vv_visualization.set_zlim([-2, 2])
        if index == 0:
            vv_visualization.quiver(0, 0, 0, self.vx[index], self.vy[index], self.vz[index], color='black', length=1.0)
        elif velocities[index] > velocities[index - 1]:
            vv_visualization.quiver(0, 0, 0, self.vx[index], self.vy[index], self.vz[index], color='green', length=1.0)
        elif velocities[index] < velocities[index - 1]:
            vv_visualization.quiver(0, 0, 0, self.vx[index], self.vy[index], self.vz[index], color='red', length=1.0)
        else:
            vv_visualization.quiver(0, 0, 0, self.vx[index], self.vy[index], self.vz[index], color='black', length=1.0)

# Create a new class for the Color Key Explanation Dialog
class ColorKeyDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Color Key Explanation")
        self.setGeometry(200, 200, 300, 150) 

        layout = QVBoxLayout()
        explanation_label = QLabel("Green: Indicates an increasing value.\n"+
                                    "Red: Indicates a decreasing value.\n"+
                                    "Black: Indicates a constant value.\n\n"+
                                    "The color of the mission status indicates the current status of the mission.\n"+
                                    "Green: Orbiting Earth\n"+
                                    "Purple: On the Way To The Moon\n"+
                                    "Brown: Returning to Earth\n"+
                                    "Orange: Entry\n"+
                                    "Pink: Descent and Landing\n\n"+
                                    "The color of the satellite connection status indicates the current connection status of the satellite.\n"+
                                    "Green: Connected\n"+
                                    "Red: Disconnected\n\n"+
                                    "The color of the connected satellites count indicates the number of connected satellites.\n"+
                                    "Green: More than 2 satellites connected\n"+
                                    "Yellow: 2 satellites connected\n"+
                                    "Red: Less than 2 satellites connected\n\n")
        layout.addWidget(explanation_label)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)

class main(QMainWindow):
    def __init__(self, data):
        super().__init__()

        # Initialize all the data sets
        
        # Position Components, 
        self.rx = data['Rx(km)[J2000-EARTH]']
        self.ry = data['Ry(km)[J2000-EARTH]']
        self.rz = data['Rz(km)[J2000-EARTH]']
        self.p_vec = [self.rx, self.ry, self.rz]

        # Velocity Components
        self.vx = data['Vx(km/s)[J2000-EARTH]']
        self.vy = data['Vy(km/s)[J2000-EARTH]']
        self.vz = data['Vz(km/s)[J2000-EARTH]']
        self.v_vec = [self.vx, self.vy, self.vz]

        self.UI()
        self.play_mode = False;
        self.paused = False;
        self.link_table_ON = True;
        self.moon_earth_ON = False;
        self.current_index = 0
        self.distance_data_visible = True  # Track visibility of distance data
        self.vector_data_visible = True  # Track visibility of vector data
        self.raw_time_visible = True  # Track visibility of raw time data
        self.velocity_vector_visual_visible = True  # Track visibility of the velocity vector visual
        self.COLOR_ON = True
        

    def UI(self):
        # All the UI Setup/Initialization

        self.setWindowTitle("Artemis II Mission Simulation")
        self.setGeometry(100, 100, 1200, 900)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)  
        


        # Remove the tabbed layout
        # Right side
        right_panel = QWidget()  # Change from QTabWidget to QWidget
        right_layout = QVBoxLayout(right_panel)  # Use a vertical layout

        #Metrics Panel
        metrics_widget = QWidget()
        metrics_layout = QVBoxLayout(metrics_widget)

        self.mission_metrics_label = QLabel("Mission Metrics")
        self.mission_metrics_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #004080;")
        
        self.resultant_velocity_label = QLabel("Resultant Velocity: Hover Over A Point!")
        self.resultant_velocity_label.setStyleSheet("font-size: 20px; color: #333333;")

        # metric labels
        self.time_label = QLabel("Time: Hover Over A Point!")
        self.time_label.setStyleSheet("font-size: 20px; color: #333333;")
        self.raw_time_label = QLabel("Time: Hover Over A Point!")
        self.raw_time_label.setStyleSheet("font-size: 20px; color: #333333;")
        self.mission_status_label = QLabel("Mission Status: Hover Over A Point!")
        self.mission_status_label.setStyleSheet("font-size: 20px; color: #333333;")
        

        #velocity magnitude
        self.velocity_label = QLabel("Velocity: Hover Over A Point!")
        self.velocity_label.setStyleSheet("font-size: 20px; color: #333333;")

        #distances
        self.distance_E_label = QLabel("Distance From Earth: Hover Over A Point!")
        self.distance_E_label.setStyleSheet("font-size: 20px; color: #333333;")
        self.distance_M_label = QLabel("Distance From Moon: Hover Over A Point!")
        self.distance_M_label.setStyleSheet("font-size: 20px; color: #333333;")
        self.total_distance_label = QLabel("Total Distance Covered: Hover Over A Point!")
        self.total_distance_label.setStyleSheet("font-size: 20px; color: #333333;")

        
        #vectors
        self.position_label = QLabel("Position Vector: Hover Over A Point!")
        self.position_label.setStyleSheet("font-size: 20px; color: #333333;")
        self.velocity_vector_label = QLabel("Velocity Vector: Hover Over A Point!")
        self.velocity_vector_label.setStyleSheet("font-size: 20px; color: #333333;")
        


        self.satellite_title = QLabel("Satellite Prioritization Table by Link Budget")
        self.satellite_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #004080;")

        self.connected_satellites = QLabel("Connected Satellites: Hover Over A Point!")
        self.connected_satellites.setStyleSheet("font-size: 20px; color: #333333;")

        self.connected_satellites_count_visual = QLabel()  # Add a label for visual representation
        self.connected_satellites_count_visual.setFixedSize(200, 20)  # Set a fixed size for the visual
        self.connected_satellites_count_visual.setStyleSheet("border: 1px solid black;")

        self.satellite_link_table = QTableWidget(self)
        self.satellite_link_table.setGeometry(50, 120, 350, 400)        
        self.update_satellite_link_table(0)

        self.satellite_table_button = QPushButton("Toggle to Priority Table by Least Switches")
        self.satellite_table_button.setStyleSheet("font-size: 16px;")
        self.satellite_table_button.clicked.connect(self.toggle_satellite_table)

        self.velocity_metrics_label = QLabel("Velocity Metrics")
        self.velocity_metrics_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #004080;")

        self.state_widgets = [self.time_label, self.distance_E_label, self.velocity_label, self.position_label]
        
        #The order of the widgets in the layout
        metrics_layout.addWidget(self.mission_metrics_label)
        
        #general metrics
        # metrics_layout.addWidget(self.time_label)
        metrics_layout.addWidget(self.raw_time_label)
        metrics_layout.addWidget(self.mission_status_label)
        # metrics_layout.addWidget(self.velocity_label)

        #distance labels
        metrics_layout.addWidget(self.distance_E_label)
        metrics_layout.addWidget(self.distance_M_label)
        metrics_layout.addWidget(self.total_distance_label)

        #vector labels
        metrics_layout.addWidget(self.position_label)
        

        # Add the resultant velocity label to the metrics layout

        metrics_layout.addWidget(self.satellite_title)
        metrics_layout.addWidget(self.connected_satellites)
        metrics_layout.addWidget(self.connected_satellites_count_visual)    
        metrics_layout.addWidget(self.satellite_table_button)
        metrics_layout.addWidget(self.satellite_link_table)

        metrics_layout.addWidget(self.velocity_metrics_label)
        metrics_layout.addWidget(self.resultant_velocity_label)
        metrics_layout.addWidget(self.velocity_vector_label)
        self.velocity_canvas = Velocity_visual(self.v_vec)
        metrics_layout.addWidget(self.velocity_canvas)
        metrics_layout.addStretch()  

        self.distance_toggle_checkbox = QCheckBox("Show Distance Data")
        self.vector_toggle_checkbox = QCheckBox("Show Vector Data")
        self.COLOR_ON_toggle_checkbox = QCheckBox("Turn On Color")
        self.velocity_vector_visual_toggle = QCheckBox("Show Velocity Vector Visual")

        self.distance_toggle_checkbox.setChecked(False)
        self.vector_toggle_checkbox.setChecked(False)
        self.COLOR_ON_toggle_checkbox.setChecked(True)
        self.velocity_vector_visual_toggle.setChecked(True)

        self.distance_toggle_checkbox.stateChanged.connect(self.toggle_distance_data)
        self.vector_toggle_checkbox.stateChanged.connect(self.toggle_vector_data)
        self.COLOR_ON_toggle_checkbox.stateChanged.connect(self.COLOR_ON_toggle)
        self.velocity_vector_visual_toggle.stateChanged.connect(self.toggle_velocity_vector_visual)

        metrics_layout.addWidget(self.distance_toggle_checkbox)
        metrics_layout.addWidget(self.vector_toggle_checkbox)
        metrics_layout.addWidget(self.COLOR_ON_toggle_checkbox)
        metrics_layout.addWidget(self.velocity_vector_visual_toggle)
        right_layout.addWidget(metrics_widget)

        #make the distances and vectors labels invisible
        self.distance_E_label.setVisible(False)
        self.distance_M_label.setVisible(False)
        self.total_distance_label.setVisible(False)
        self.position_label.setVisible(False)
        self.velocity_vector_label.setVisible(False)
        

        # Add the physics canvas directly to the right layout
        
        # right_layout.addWidget(self.velocity_canvas)

        # Left side: 3D canvas with the toolbar above it
        left_main_visualization = QWidget()
        mission_left_visuals = QVBoxLayout(left_main_visualization)  
        self.canvas = Flight_Sim_Visual(self.p_vec, self.state_widgets, self.velocity_canvas)
        self.canvas.index_hovered.connect(self.update_velocity_vector)  
        self.canvas.index_hovered.connect(self.update_mission_metrics)
        self.canvas.index_hovered.connect(self.update_satellite_link_table)  
        self.toolbar = NavigationToolbar(self.canvas, self)

        mission_left_visuals.addWidget(self.toolbar)  
        mission_left_visuals.addWidget(self.canvas)  

        # Left side bottom animation controls/ Controls Layout ---------------------------------

        controls_buttons_on_top = QVBoxLayout()
        controls_buttons_on_bottom = QVBoxLayout()


        self.play_analyze_button = QPushButton("Play Animation")
        self.play_analyze_button.setStyleSheet("font-size: 16px;")
        self.play_analyze_button.clicked.connect(self.toggle_animation)

        self.pause_button = QPushButton("Pause Simulation")
        self.pause_button.setStyleSheet("font-size: 16px;")
        self.pause_button.clicked.connect(self.pause_animation)

        self.restart_button = QPushButton("Restart Simulation")
        self.restart_button.setStyleSheet("font-size: 16px;")
        self.restart_button.clicked.connect(self.restart_simulation)
        
        self.moon_earth_button = QPushButton("Visualize Moon and Earth")
        self.moon_earth_button.setStyleSheet("font-size: 16px;") 
        self.moon_earth_button.clicked.connect(self.visualize_moon_earth)
        
        
        controls_buttons_on_top.addWidget(self.play_analyze_button)
        controls_buttons_on_top.addWidget(self.pause_button)
        controls_buttons_on_bottom.addWidget(self.restart_button)
        controls_buttons_on_bottom.addWidget(self.moon_earth_button)

        mission_left_visuals.addLayout(controls_buttons_on_top)
        mission_left_visuals.addLayout(controls_buttons_on_bottom)

        # add to main layout
        main_layout.addWidget(left_main_visualization, stretch=7) 



# Color Key Stuff, You got this Jacob
        main_layout.addWidget(right_panel, stretch=3)  

        self.color_key_button = QPushButton("Color Key Explanation")
        self.color_key_button.setStyleSheet("font-size: 16px;")
        self.color_key_button.clicked.connect(self.open_color_key_dialog) 
        metrics_layout.addWidget(self.color_key_button)

    def update_velocity_vector(self, index):
        GLOBAL_INDEX = index
        self.velocity_canvas.update_velocity_vector(index)
        self.velocity_canvas.draw()

    def update_path_vector(self, index):
        self.canvas.update_path(index)
        self.canvas.draw()
        
    def update_mission_metrics(self, index):

        prev_index = index - 1
        if index == 0:
            prev_index = 0
        
    
        update_label_color(self.distance_E_label, distances[index], distances[prev_index], self.COLOR_ON)
        update_label_color(self.resultant_velocity_label, velocities[index], velocities[prev_index], self.COLOR_ON)
        update_label_color(self.distance_M_label, data["Moon Distance(km)[J2000-EARTH]"][index], data["Moon Distance(km)[J2000-EARTH]"][prev_index], self.COLOR_ON)
        update_label_color(self.total_distance_label, data["Total Distance(km)[J2000-EARTH]"][index], data["Total Distance(km)[J2000-EARTH]"][prev_index], self.COLOR_ON)



        # self.time_label.setText("Time(UTC): " + time_adder(round(times[index],0)) + "")
        self.raw_time_label.setText("Time: " + str(round(times[index], 2)) + " mins")
        self.mission_status_label.setText("Mission Status: " + data["Mission Status"][index])
        self.mission_status_label.setStyleSheet("font-size: 20px; color: " + (mission_status_color(index,self.COLOR_ON)) + ";")
        self.velocity_label.setText("Position Vector: <" + str(round(self.rx[index],2)) + "," + str(round(self.ry[index],2)) + ","+ str(round(self.rz[index],2)) + "> km")

        self.distance_E_label.setText("Distance From Earth: " +str(round(distances[index],2)) + "km")
        self.distance_M_label.setText("Distance From Moon: " + str(round(data["Moon Distance(km)[J2000-EARTH]"][index], 2)) + " km")
        self.total_distance_label.setText("Total Distance Covered: " + str(round(data["Total Distance(km)[J2000-EARTH]"][index], 2)) + " km")

        self.position_label.setText("Position Vector: <" + str(round(self.rx[index],2)) + "," + str(round(self.ry[index],2)) + ","+ str(round(self.rz[index],2)) + "> km")
        self.velocity_vector_label.setText("Velocity Vector: <" + str(round(self.vx[index],2)) + "," + str(round(self.vy[index],2)) + ","+ str(round(self.vz[index],2)) + "> km/s")
        self.resultant_velocity_label.setText("Resultant Velocity: "+ str(round(velocities[index],2)) + " km/s")
        
        self.connected_satellites.setText("Connected Satellites: " + str(data["Connected Satellites Count"][index]))

        connected_count = data["Connected Satellites Count"][index]
        
        if connected_count > 2:
            self.connected_satellites_count_visual.setStyleSheet("background-color: green; border: 1px solid black;")
        elif connected_count == 2:
            self.connected_satellites_count_visual.setStyleSheet("background-color: yellow; border: 1px solid black;")
        else:
            self.connected_satellites_count_visual.setStyleSheet("background-color: red; border: 1px solid black;")

    def toggle_animation(self):
        if(self.play_mode == False):
            self.play_mode = True
            self.play_analyze_button.setText("Analyze path")                  
            self.canvas.play_flight_animation(self.state_widgets,self.velocity_canvas, self)
        else:
            self.play_mode = False
            self.play_analyze_button.setText("Run Simulation")
            self.canvas.plot_static_path()
        self.canvas.draw()
    
    def pause_animation(self):
        if(self.paused == True):
            self.canvas.play_flight_animation(self.state_widgets,self.velocity_canvas, self)
            self.pause_button.setText("Pause Simulation")       
            self.paused = False
        else:
            self.pause_button.setText("Resume Simulation")
            self.canvas.pause_flight_animation()
            self.paused = True
    
    def restart_simulation(self):
        self.canvas.restart_flight_animation(self.state_widgets, self.velocity_canvas, self)
        self.canvas.draw()

    def update_satellite_link_table(self,index):
        self.current_index = index
        if not hasattr(self, 'link_table_ON'):
            self.link_table_ON = True
        if(self.link_table_ON == True):
            self.satellite_link_table.setRowCount(4)
            self.satellite_link_table.setColumnCount(3)

            self.satellite_link_table.setHorizontalHeaderLabels([emoji.emojize("Satellite :satellite:"), emoji.emojize("Bitrate(kps):laptop:"), emoji.emojize("Connection Status:antenna_bars:")])

            font = QFont()
            font.setPointSize(13)
            ordered_satellites = []
            key_order = data["Link Budget Prioritization"][index].split(",")
            for key in key_order:
                ordered_satellites.append(key_to_satellite_name(int(key)))
            
            table_data = []
            for satellite_name in ordered_satellites:
                row = []
                row.append(satellite_name)
                row.append(str(round(data[satellite_name + " Bit Rate"][index],0)))
                row.append("Available" if data[satellite_name][index] > 0 else "Disconnected")
                table_data.append(row)

            for row, rowData in enumerate(table_data):
                for column, value in enumerate(rowData):
                    connection_status = QTableWidgetItem(value)
                    if column == 2:
                        if value == "Available":
                            connection_status.setForeground(QColor("green"))
                        else:
                            connection_status.setForeground(QColor("red"))
                    self.satellite_link_table.setItem(row, column, connection_status)

            self.satellite_link_table.setFont(font)
            self.satellite_link_table.resizeColumnsToContents()
        else:

            self.satellite_link_table.setRowCount(4)
            self.satellite_link_table.setColumnCount(2)

            self.satellite_link_table.setHorizontalHeaderLabels([emoji.emojize("Satellite :satellite:"),emoji.emojize("Connection Status :antenna_bars:")])

            font = QFont()
            font.setPointSize(13)
            ordered_satellites = []
            key_order = data["Switches Prioritization"][index].split(",")
            for key in key_order:
                ordered_satellites.append(key_to_satellite_name(int(key)))
            
            table_data = []
            for satellite_name in ordered_satellites:
                row = []
                row.append(satellite_name)
                row.append(("Connected") if data[satellite_name][index] > 0 else ("Disconnected"))
                table_data.append(row)

            for row, rowData in enumerate(table_data):
                for column, value in enumerate(rowData):
                    connection_status = QTableWidgetItem(value)
                    if column == 1:
                        if value == "Connected":
                            connection_status.setForeground(QColor("green"))
                            value = "Available"
                        else:
                            connection_status.setForeground(QColor("red"))
                    self.satellite_link_table.setItem(row, column, connection_status)

            self.satellite_link_table.setFont(font)
            self.satellite_link_table.resizeColumnsToContents()
        self.satellite_link_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.satellite_link_table.setMaximumHeight(200)
        self.satellite_link_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.satellite_link_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    
    def toggle_satellite_table(self):
        if(self.link_table_ON == False):
            self.link_table_ON = True
            self.satellite_table_button.setText("Toggle to Priority Table by Least Switches")
            self.satellite_title.setText("Satellite Prioritization Table by Link Budget")     
            self.update_satellite_link_table(self.current_index)
        else:
            self.link_table_ON = False
            self.satellite_table_button.setText("Toggle to Priority Table by Link Budget")
            self.satellite_title.setText("Satellite Prioritization Table by Least Switches")
            self.update_satellite_link_table(self.current_index)
    
   

    def visualize_moon_earth(self):
        if(self.moon_earth_ON == False):
            self.moon_earth_ON = True
            self.moon_earth_button.setText("Hide Moon and Earth")
            self.canvas.add_moon_earth()
        else:
            self.moon_earth_ON = False
            self.moon_earth_button.setText("Visualize Moon and Earth")
            self.canvas.remove_moon_earth(self.state_widgets, self.velocity_canvas,self)
    
    def toggle_distance_data(self):
        self.distance_data_visible = self.distance_toggle_checkbox.isChecked()
        self.distance_E_label.setVisible(self.distance_data_visible)
        self.distance_M_label.setVisible(self.distance_data_visible)
        self.total_distance_label.setVisible(self.distance_data_visible)

    def toggle_vector_data(self):
        self.vector_data_visible = self.vector_toggle_checkbox.isChecked()
        self.position_label.setVisible(self.vector_data_visible)
        self.velocity_vector_label.setVisible(self.vector_data_visible)

    def COLOR_ON_toggle(self):
        self.COLOR_ON = self.COLOR_ON_toggle_checkbox.isChecked()
        if self.COLOR_ON == False:
            self.connected_satellites_count_visual.setVisible(False)
        else:
            self.connected_satellites_count_visual.setVisible(True)
    
    def toggle_velocity_vector_visual(self):
        self.velocity_vector_visual_visible = self.velocity_vector_visual_toggle.isChecked()
        self.velocity_canvas.setVisible(self.velocity_vector_visual_visible)

    def open_color_key_dialog(self):
        dialog = ColorKeyDialog()
        dialog.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = main(data)
    window.show()
    sys.exit(app.exec_())