if __name__ == "__main__" :
    print("\033cStarting ...\n") # Close Terminal

import csv                      # For csv writing
import os                       # To manage folders and paths
import sys                      # For quitting program early
from time import sleep, time    # To get time and wait

try :
    import cv2      # For the camera
    import ximu3    # For the IMU
except ModuleNotFoundError as Err :
    missing_module = str(Err).replace('No module named ','')
    missing_module = missing_module.replace("'",'')
    if missing_module == 'cv2' :
        sys.exit(f'No module named {missing_module} try : pip install opencv-python')
    else :
        print(f'No module named {missing_module} try : pip install {missing_module}')

try :
    from Imports.Functions import format_time, connected_wifi
except ModuleNotFoundError :
    sys.exit('Missing Import folder, make sure you are in the right directory')

root_directory = 'Temporary Data'   # Directory where temporary folders are stored
cam_num = 0                         # Set to 0 to activate the camera, but 1 if yoy have a builtin camera
fps = 30                            # Number of save per seconds
buffer = 10                         # Number of folders saved
CleanFolder: bool = True            # If True, delete all temporary folders at the end
wifi_to_connect = 'Upper_Limb_Exo'  # The Wi-Fi where the raspberry pi and IMUs are connected


if not connected_wifi() == wifi_to_connect and not connected_wifi() == wifi_to_connect+'_5G' :
    sys.exit('Not connected to the right wifi')

# Initialize sensor values to 0
gyr_x_1 = gyr_y_1 = gyr_z_1 = 0
acc_x_1 = acc_y_1 = acc_z_1 = 0
gyr_x_2 = gyr_y_2 = gyr_z_2 = 0
acc_x_2 = acc_y_2 = acc_z_2 = 0

# We check if the root directory exist
if not os.path.exists(root_directory) :
    os.makedirs(root_directory)
elif os.listdir(root_directory):  # If there are files in the directory : True
    ask_clear = str(input(f'\033c{root_directory} not empty do you want to clear it ? (Y/N)'))
    while True:
        if ask_clear.upper() == "Y" or ask_clear.upper() == "YES" :
            for folders_to_del in os.listdir(root_directory):
                for files_to_del in os.listdir(f"{root_directory}/{folders_to_del}"):
                    os.remove(os.path.join(f'{root_directory}/{folders_to_del}', files_to_del))
                os.rmdir(f"{root_directory}/{folders_to_del}")
            break
        elif ask_clear.upper() == "N" or ask_clear.upper() == "NO" :
            sys.exit('Cannot access non-empty folder')
        else : ask_clear = str(input('Yes or No :'))

print("\033cStarting ...\n") # Close Terminal



# Connection class
class Connection:
    def __init__(self, connection_info):
        self.__connection = ximu3.Connection(connection_info)

        if self.__connection.open() != ximu3.RESULT_OK:
            sys.exit("Unable to open connection " + connection_info.to_string())

        ping_response = self.__connection.ping()

        if ping_response.result != ximu3.RESULT_OK:
            print("Ping failed for " + connection_info.to_string())
            raise AssertionError

        self.__prefix = ping_response.serial_number
        self.__connection.add_inertial_callback(self.__inertial_callback)

    def close(self):
        self.__connection.close()

    def send_command(self, key, value=None):
        if value is None:
            value = "null"
        elif type(value) is bool:
            value = str(value).lower()
        elif type(value) is str:
            value = "\"" + value + "\""
        else:
            value = str(value)

        command = "{\"" + key + "\":" + value + "}"

        responses = self.__connection.send_commands([command], 2, 500)

        if not responses:
            sys.exit("Unable to confirm command " + command + " for " + self.__connection.get_info().to_string())
        else:
            print(self.__prefix + " " + responses[0])

    def __inertial_callback(self, message):
        global gyr_x_1, gyr_y_1, gyr_z_1
        global acc_x_1, acc_y_1, acc_z_1
        global gyr_x_2, gyr_y_2, gyr_z_2
        global acc_x_2, acc_y_2, acc_z_2
        if self.__prefix == '65577B49':
            gyr_x_1 = message.gyroscope_x
            gyr_y_1 = message.gyroscope_y
            gyr_z_1 = message.gyroscope_z
            acc_x_1 = message.accelerometer_x
            acc_y_1 = message.accelerometer_y
            acc_z_1 = message.accelerometer_z
        elif self.__prefix == '655782F7':
            gyr_x_2 = message.gyroscope_x
            gyr_y_2 = message.gyroscope_y
            gyr_z_2 = message.gyroscope_z
            acc_x_2 = message.accelerometer_x
            acc_y_2 = message.accelerometer_y
            acc_z_2 = message.accelerometer_z



# Establish connections
while True :
    try :
        connections = [Connection(m.to_udp_connection_info()) for m in ximu3.NetworkAnnouncement().get_messages_after_short_delay()]
        break
    except AssertionError:
        pass
if not connections:
    sys.exit("No UDP connections to IMUs")
print('Connected to IMUs\n')

sequence_length = 10    # Size of samples default 10
sample_counter = 0
frames_counter = 0


# Video capture setup
cap = cv2.VideoCapture(cam_num)
cap.set(cv2.CAP_PROP_FPS, fps)
Start_Time = time()


try : # try except is to ignore the keyboard interrupt error
    message = f'Clean Folder : {CleanFolder} \nCamera Number : {cam_num} \nProgramme running   ctrl + C to stop'
    print('\033c'+message)
    while True : # While True is an infinite loop
        sample_counter += 1

        # We create a folder with a csv file in it
        os.makedirs(f"{root_directory}/Sample_{sample_counter}")
        csv_file = open(f'{root_directory}/Sample_{sample_counter}/imu.csv', mode='w', newline='')

        # We add 1 imu data to the csv and 1 image to the folder
        for i in range(sequence_length):
            frames_counter += 1
            while time() - Start_Time < frames_counter / fps:  # To ensure 30 fps
                sleep(0.001)

            # Add IMU data
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow([gyr_x_1, gyr_y_1, gyr_z_1, acc_x_1, acc_y_1, acc_z_1,
                             gyr_x_2, gyr_y_2, gyr_z_2, acc_x_2, acc_y_2, acc_z_2])

            gyr1_vals = [round(gyr_x_1), round(gyr_y_1), round(gyr_z_1)]
            len_str_gyr1_vals = 0
            for val in gyr1_vals :
                len_str_gyr1_vals += len(str(val))
            if len_str_gyr1_vals >= 9 : tabulation = '\t'
            else : tabulation = '\t\t'
            print(gyr1_vals, tabulation,[round(gyr_x_2), round(gyr_y_2), round(gyr_z_2)])
            
            if frames_counter%50 == 0 :
                print('\033c'+message)
            


            ret, frame = cap.read()
            if not ret: # If camera is unavailable :
                # Release resources
                cap.release()
                cv2.destroyAllWindows()
                csv_file.close()
                for connection in connections:
                    connection.close()
                sys.exit('\nCamera disconnected')

            # Add image
            image_filename = f'{root_directory}/Sample_{sample_counter}/frame_{frames_counter}.jpg'
            cv2.imwrite(image_filename, frame)

        # We delete the folders as we go so that we don't saturate
        if sample_counter > buffer:
            for files_to_del in os.listdir(f"{root_directory}/Sample_{sample_counter - buffer}"):
                os.remove(os.path.join(f'{root_directory}/Sample_{sample_counter - buffer}', files_to_del))
            os.rmdir(f"{root_directory}/Sample_{sample_counter - buffer}")

except KeyboardInterrupt :
    t = round(time() - Start_Time, 4)
    print(f"\n{frames_counter} images were saved in {format_time(t)}  -  fps : {frames_counter / t}")

    try : # We use try because csv_file can be undefined
        csv_file.close()
    except NameError:
        pass

    if CleanFolder:
        for folders_left in os.listdir(root_directory) :
            for files_left in os.listdir(f"{root_directory}/{folders_left}"):
                os.remove(os.path.join(f'{root_directory}/{folders_left}', files_left))
            os.rmdir(f"{root_directory}/{folders_left}")
        os.rmdir(root_directory)
    print('\nProgramme Stopped\n')


# Release resources
cap.release()
cv2.destroyAllWindows()
csv_file.close()
for connection in connections:
    connection.close()


