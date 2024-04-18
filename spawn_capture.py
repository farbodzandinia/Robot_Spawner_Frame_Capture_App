#!/usr/bin/env python3

from PyQt5 import uic
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtGui import QImage, QPixmap

from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from gazebo_msgs.srv import SetModelState, SetModelStateRequest

import sys
import os
import signal
import rospy
from datetime import datetime

class RSFCApp(QMainWindow):
    def __init__(self):
        super(RSFCApp, self).__init__()
        """
        Initializes the RSFCApp GUI application.
        Sets up the user interface from a .ui file, initializes ROS node,
        connects GUI elements to functionality, and subscribes to necessary ROS topics.
        """
        # Load the .ui file
        uic.loadUi('spawn_capture.ui', self)

        # ROS initialization
        rospy.init_node('rsfc_app_ui', anonymous=True)
        self.bridge = CvBridge()

        # Connect buttons
        self.spawn_button.clicked.connect(self.spawn_robot)
        self.capture_button.clicked.connect(self.capture_frame)

        # Subscribe to the camera feed
        self.subscriber = rospy.Subscriber("/R1/pi_camera/image_raw", Image, self.update_camera_feed)

        # For capturing screenshots
        self.current_frame = None

    def spawn_robot(self):
        """
        Spawns a robot model in the simulation environment.
        Retrieves robot position and orientation from the GUI and sends a request
        to the ROS service to update the robot's state in the Gazebo simulator.
        """
        coordinate_x = self.coordinate_x.value()
        coordinate_y = self.coordinate_y.value()
        coordinate_z = self.coordinate_z.value()
        orientation_z = self.orientation_z.value()
        orientation_w = self.orientation_w.value()

        msg = SetModelStateRequest()
        msg.model_state.model_name = 'R1'
        msg.model_state.pose.position.x = coordinate_x * -1 # Coordinates are inverted
        msg.model_state.pose.position.y = coordinate_y * -1 # Coordinates are inverted
        msg.model_state.pose.position.z = coordinate_z
        msg.model_state.pose.orientation.x = 0 # Not important
        msg.model_state.pose.orientation.y = 0 # Not important
        msg.model_state.pose.orientation.z = orientation_z
        msg.model_state.pose.orientation.w = orientation_w

        try:
            rospy.wait_for_service('/gazebo/set_model_state')
            set_state = rospy.ServiceProxy('/gazebo/set_model_state', SetModelState)
            set_state(msg)
        except rospy.ServiceException as e:
            rospy.logerr(e)

    def update_camera_feed(self, data):
        """
        Updates the GUI to display the latest frame from the robot's camera.
        Converts the ROS image message to a QImage and displays it on the GUI.
        """
        cv_image = self.bridge.imgmsg_to_cv2(data, "bgr8")
        height, width, channel = cv_image.shape
        bytes_per_line = 3 * width
        self.current_frame = QImage(cv_image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        self.camera_feed.setPixmap(QPixmap.fromImage(self.current_frame))

    def capture_frame(self):
        """
        Captures the current frame from the camera feed and saves it as a PNG image.
        Constructs a file name using the current timestamp and updates the GUI
        to reflect the save status.
        """
        if self.current_frame:
            
            folder_path = "screenshots"
            # Ensure the folder exists
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

            # Get the current time
            now = datetime.now()
            # Format the time in a file-friendly format (e.g., YYYYMMDD_HHMMSS)
            timestamp = now.strftime("%Y-%m-%d_%H:%M:%S")
            # Use the timestamp in the file name
            screenshot_path = os.path.join(folder_path, f"camera_feed_screenshot_{timestamp}.png")
            self.current_frame.save(screenshot_path, "PNG")
        
            # Update the QLineEdit widget with the message including the timestamp
            self.capture_frame_output.setText(f"Screenshot saved at {timestamp} in 'pwd/{folder_path}'")
        else:
            # If there's no current frame, you might want to indicate that as well
            self.capture_frame_output.setText("No screenshot captured. Camera feed might be empty.")

if __name__ == '__main__':
    """
    Main entry point of the application. Initializes the application,
    sets up the main window, handles system signals, and starts the Qt event loop.
    """
    app = QApplication(sys.argv)
    
    # Handle SIGINT to close the application
    signal.signal(signal.SIGINT, lambda *args: app.quit())

    window = RSFCApp()
    window.show()
    
    # Use a timer to handle events every 500 milliseconds to process the SIGINT and other events
    timer = QTimer()
    timer.start(500)  # in milliseconds
    timer.timeout.connect(lambda: None)  # Do nothing on timeout, just process events

    sys.exit(app.exec_())