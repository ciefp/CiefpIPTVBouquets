import os
import requests
from Components.Pixmap import Pixmap
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from enigma import eDVBDB

PLUGIN_VERSION = "1.2"  # Updated version
PLUGIN_NAME = "CiefpIPTVBouquets"
PLUGIN_DESCRIPTION = "Enigma2 IPTV Bouquets"
GITHUB_API_URL = "https://api.github.com/repos/ciefp/CiefpIPTV/contents/"
BOUQUET_PATH = "/etc/enigma2/"

class CiefpIPTV(Screen):
    skin = """
        <screen position="center,center" size="1600,800" title="..:: Ciefp IPTV Bouquets ::..    (Version{version})">
            <widget name="left_list" position="0,0" size="620,700" scrollbarMode="showAlways" itemHeight="33" font="Regular;28" />
            <widget name="right_list" position="630,0" size="610,700" scrollbarMode="showAlways" itemHeight="33" font="Regular;28" />
            <widget name="background" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpIPTVBouquets/background.png" position="1240,0" size="360,800" />
            <widget name="status" position="0,710" size="840,50" font="Regular;24" />
            <widget name="green_button" position="0,750" size="150,35" font="Bold;28" halign="center" backgroundColor="#1F771F" foregroundColor="#000000" />
            <widget name="yellow_button" position="170,750" size="150,35" font="Bold;28" halign="center" backgroundColor="#9F9F13" foregroundColor="#000000" />
            <widget name="red_button" position="340,750" size="150,35" font="Bold;28" halign="center" backgroundColor="#9F1313" foregroundColor="#000000" />
            <widget name="blue_button" position="510,750" size="150,35" font="Bold;28" halign="center" backgroundColor="#132B9F" foregroundColor="#000000" />
            <widget name="version_info" position="680,750" size="480,40" font="Regular;20" foregroundColor="#FFFFFF" />
        </screen>
    """.format(version=PLUGIN_VERSION)

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.selected_bouquets = []
        self.bouquet_files = {}
        
        self["left_list"] = MenuList([])
        self["right_list"] = MenuList([])
        self["background"] = Pixmap()
        self["status"] = Label("Loading bouquets...")
        self["green_button"] = Label("Select")
        self["yellow_button"] = Label("Install")
        self["red_button"] = Label("IPTV Manager")  # Changed from Exit to IPTV Manager
        self["blue_button"] = Label("Cleaner")
        self["version_info"] = Label(f"Version: {PLUGIN_VERSION}")
        
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.select_item,
            "cancel": self.exit,
            "up": self.up,
            "down": self.down,
            "green": self.select_item,
            "yellow": self.install,
            "red": self.open_iptv_manager,  # Changed from exit to open_iptv_manager
            "blue": self.open_cleaner
        }, -1)
        
        self.onLayoutFinish.append(self.load_bouquets)

    def load_bouquets(self):
        self["status"].setText("Fetching bouquets from GitHub...")
        try:
            response = requests.get(GITHUB_API_URL)
            response.raise_for_status()
            files = response.json()
            
            self.bouquet_files.clear()
            bouquet_list = []
            
            for file in files:
                if isinstance(file, dict) and file.get("name", "").endswith(".tv"):
                    filename = file["name"]
                    download_url = file["download_url"]
                    
                    file_response = requests.get(download_url)
                    file_content = file_response.text.splitlines()
                    display_name = filename.replace("userbouquet.", "").replace(".tv", "")
                    
                    for line in file_content:
                        if line.startswith("#NAME"):
                            display_name = line.replace("#NAME", "").strip()
                            break
                    
                    self.bouquet_files[display_name] = {
                        "filename": filename,
                        "download_url": download_url
                    }
                    bouquet_list.append(display_name)
            
            if not bouquet_list:
                self["status"].setText("No bouquet files found!")
                return
                
            self["left_list"].setList(bouquet_list)
            self["status"].setText("Bouquets loaded successfully")
        except Exception as e:
            self["status"].setText(f"Error loading bouquets: {str(e)}")

    def select_item(self):
        selected = self["left_list"].getCurrent()
        if selected:
            if selected in self.selected_bouquets:
                self.selected_bouquets.remove(selected)
            else:
                self.selected_bouquets.append(selected)
            self["right_list"].setList(self.selected_bouquets)

    def install(self):
        if not self.selected_bouquets:
            self.session.open(MessageBox, "No bouquets selected!", MessageBox.TYPE_ERROR)
            return
            
        self.session.openWithCallback(
            self.install_confirmed,
            MessageBox,
            "Install selected bouquets?",
            MessageBox.TYPE_YESNO
        )

    def install_confirmed(self, result):
        if not result:
            return
            
        self["status"].setText("Installing bouquets...")
        try:
            bouquets_tv_path = os.path.join(BOUQUET_PATH, "bouquets.tv")
            
            for bouquet in self.selected_bouquets:
                bouquet_info = self.bouquet_files.get(bouquet)
                if not bouquet_info:
                    continue
                    
                filename = bouquet_info["filename"]
                download_url = bouquet_info["download_url"]
                destination = os.path.join(BOUQUET_PATH, filename)
                
                response = requests.get(download_url)
                response.raise_for_status()
                
                content = response.text
                if not content.startswith("#NAME"):
                    raise ValueError(f"Invalid bouquet file format: {filename}")
                
                with open(destination, "w") as f:
                    f.write(content)
                
                service_line = f'#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "{filename}" ORDER BY bouquet\n'
                if os.path.exists(bouquets_tv_path):
                    with open(bouquets_tv_path, "r") as f:
                        existing_lines = f.readlines()
                    if service_line not in existing_lines:
                        with open(bouquets_tv_path, "a") as f:
                            f.write(service_line)
                else:
                    with open(bouquets_tv_path, "w") as f:
                        f.write(service_line)
            
            self["status"].setText("Bouquets installed successfully!")
            self.selected_bouquets = []
            self["right_list"].setList([])
            
            self.session.openWithCallback(
                self.reload_confirm,
                MessageBox,
                "Do you want to reload settings now?",
                MessageBox.TYPE_YESNO
            )
            
        except Exception as e:
            self["status"].setText(f"Error installing bouquets: {str(e)}")

    def reload_confirm(self, result):
        if result:
            self.reload_settings()

    def reload_settings(self):
        try:
            eDVBDB.getInstance().reloadServicelist()
            eDVBDB.getInstance().reloadBouquets()
            self.session.open(
                MessageBox,
                "Reload successful! New bouquets are now active. .::ciefpsettings::.",
                MessageBox.TYPE_INFO,
                timeout=5
            )
        except Exception as e:
            self.session.open(
                MessageBox,
                "Reload failed: " + str(e),
                MessageBox.TYPE_ERROR,
                timeout=5
            )

    def up(self):
        self["left_list"].up()

    def down(self):
        self["down"].down()

    def exit(self):
        self.close()

    def open_cleaner(self):
        self.session.open(BouquetCleaner)

    def open_iptv_manager(self):
        self.session.open(IPTVManager)

class BouquetCleaner(Screen):
    skin = """
        <screen name="bouquetcleaner" position="center,center" size="1200,800" title="..:: Deleted Bouquets ::..">
            <widget name="channel_list" position="20,20" size="830,700" scrollbarMode="showOnDemand" itemHeight="33" font="Regular;28" />
            <widget name="background" position="850,0" size="350,800" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpIPTVBouquets/background2.png" zPosition="-1" alphatest="on" />
            <widget name="button_red" position="20,740" size="180,40" font="Bold;22" halign="center" backgroundColor="#9F1313" foregroundColor="#000000" />
            <widget name="button_green" position="220,740" size="180,40" font="Bold;22" halign="center" backgroundColor="#1F771F" foregroundColor="#000000" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.selected_file = None
        self.del_files = []

        # UI Components
        self["channel_list"] = MenuList([])
        self["background"] = Pixmap()
        self["button_red"] = Label("Delete")
        self["button_green"] = Label("Select All")

        # Actions
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.select_file,
            "cancel": self.exit,
            "up": self.up,
            "down": self.down,
            "red": self.delete_selected,
            "green": self.select_all
        }, -1)

        self.onLayoutFinish.append(self.load_deleted_bouquets)

    def load_deleted_bouquets(self):
        self.del_files = [f for f in os.listdir(BOUQUET_PATH) if f.endswith(".del")]
        if not self.del_files:
            self["channel_list"].setList(["No .del files found"])
        else:
            self["channel_list"].setList(self.del_files)

    def select_file(self):
        current = self["channel_list"].getCurrent()
        if current and current != "No .del files found":
            self.selected_file = current
            self["channel_list"].setList([f"{f} {'[SELECTED]' if f == self.selected_file else ''}" for f in self.del_files])

    def select_all(self):
        if self.del_files:
            self.selected_file = None  # Reset single selection
            self["channel_list"].setList([f"{f} [SELECTED]" for f in self.del_files])

    def delete_selected(self):
        if not self.del_files:
            self.session.open(MessageBox, "No .del files to delete!", MessageBox.TYPE_INFO)
            return

        to_delete = []
        if self.selected_file:
            to_delete = [self.selected_file]
        else:
            # If all are selected (no single selection)
            current_list = self["channel_list"].getList()
            if all("[SELECTED]" in item for item in current_list):
                to_delete = self.del_files

        if not to_delete:
            self.session.open(MessageBox, "No files selected for deletion!", MessageBox.TYPE_ERROR)
            return

        try:
            for file in to_delete:
                os.remove(os.path.join(BOUQUET_PATH, file))
            self.session.open(MessageBox, f"Deleted {len(to_delete)} file(s) successfully!", MessageBox.TYPE_INFO)
            self.load_deleted_bouquets()  # Refresh list
            self.selected_file = None
        except Exception as e:
            self.session.open(MessageBox, f"Error deleting files: {str(e)}", MessageBox.TYPE_ERROR)

    def up(self):
        self["channel_list"].up()

    def down(self):
        self["channel_list"].down()

    def exit(self):
        self.close()
        
class IPTVManager(Screen):
    skin = """
        <screen name="iptvmanager" position="center,center" size="1200,800" title="..:: IPTV Manager ::..">
            <widget name="channel_list" position="20,20" size="830,700" scrollbarMode="showOnDemand" itemHeight="33" font="Regular;28" />
            <widget name="background" position="850,0" size="350,800" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpIPTVBouquets/background3.png" zPosition="-1" alphatest="on" />
            <widget name="button_red" position="20,740" size="180,40" font="Bold;22" halign="center" backgroundColor="#9F1313" foregroundColor="#000000" />
            <widget name="button_green" position="220,740" size="180,40" font="Bold;22" halign="center" backgroundColor="#1F771F" foregroundColor="#000000" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.selected_bouquets = []
        self.iptv_files = []

        self["channel_list"] = MenuList([])
        self["background"] = Pixmap()
        self["button_red"] = Label("Delete")
        self["button_green"] = Label("Select")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.select_bouquet,
            "cancel": self.exit,
            "up": self.up,
            "down": self.down,
            "red": self.delete_selected,
            "green": self.select_bouquet
        }, -1)

        self.onLayoutFinish.append(self.load_iptv_bouquets)

    def load_iptv_bouquets(self):
        self.iptv_files = []
        display_names = []
        bouquets_order = []
        
        # First, read the order from bouquets.tv
        bouquets_tv_path = os.path.join(BOUQUET_PATH, "bouquets.tv")
        if os.path.exists(bouquets_tv_path):
            with open(bouquets_tv_path, "r") as f:
                for line in f:
                    if "#SERVICE" in line and "FROM BOUQUET" in line:
                        # Extract filename from service line
                        start = line.find('"') + 1
                        end = line.find('"', start)
                        if start > 0 and end > start:
                            filename = line[start:end]
                            bouquets_order.append(filename)

        # Get all IPTV files
        all_files = {}
        for f in os.listdir(BOUQUET_PATH):
            if (f.startswith("userbouquet.ciefpsettings") or 
                f.startswith("userbouquet.iptv") or 
                "iptv" in f.lower()) and f.endswith(".tv"):
                bouquet_path = os.path.join(BOUQUET_PATH, f)
                display_name = f
                
                try:
                    with open(bouquet_path, "r") as file:
                        for line in file:
                            if line.startswith("#NAME"):
                                display_name = line.replace("#NAME", "").strip()
                                break
                except:
                    display_name = f.replace("userbouquet.", "").replace(".tv", "")
                
                all_files[f] = display_name

        # Sort files according to bouquets.tv order
        ordered_files = []
        for filename in bouquets_order:
            if filename in all_files:
                ordered_files.append((filename, all_files[filename]))
                del all_files[filename]
        
        # Add remaining files (those not in bouquets.tv) at the end
        for filename, display_name in all_files.items():
            ordered_files.append((filename, display_name))

        # Update iptv_files and display_names
        self.iptv_files = [f[0] for f in ordered_files]
        display_names = [f[1] for f in ordered_files]
        
        if not display_names:
            self["channel_list"].setList(["No IPTV bouquets found"])
        else:
            self["channel_list"].setList(display_names)

    def select_bouquet(self):
        current = self["channel_list"].getCurrent()
        if current and current != "No IPTV bouquets found":
            if current in self.selected_bouquets:
                self.selected_bouquets.remove(current)
            else:
                self.selected_bouquets.append(current)
            self.update_list()

    def update_list(self):
        display_names = []
        for i, f in enumerate(self.iptv_files):
            bouquet_path = os.path.join(BOUQUET_PATH, f)
            display_name = f
            try:
                with open(bouquet_path, "r") as file:
                    for line in file:
                        if line.startswith("#NAME"):
                            display_name = line.replace("#NAME", "").strip()
                            break
            except:
                display_name = f.replace("userbouquet.", "").replace(".tv", "")
            
            if display_name in self.selected_bouquets:
                display_name += " [SELECTED]"
            display_names.append(display_name)
        self["channel_list"].setList(display_names)

    def delete_selected(self):
        if not self.selected_bouquets:
            self.session.open(MessageBox, "No bouquets selected for deletion!", MessageBox.TYPE_ERROR)
            return

        try:
            for bouquet in self.selected_bouquets:
                for i, f in enumerate(self.iptv_files):
                    display_name = f
                    bouquet_path = os.path.join(BOUQUET_PATH, f)
                    try:
                        with open(bouquet_path, "r") as file:
                            for line in file:
                                if line.startswith("#NAME"):
                                    display_name = line.replace("#NAME", "").strip()
                                    break
                    except:
                        display_name = f.replace("userbouquet.", "").replace(".tv", "")
                    
                    if display_name == bouquet:
                        os.remove(bouquet_path)
                        # Remove from bouquets.tv
                        bouquets_tv_path = os.path.join(BOUQUET_PATH, "bouquets.tv")
                        if os.path.exists(bouquets_tv_path):
                            with open(bouquets_tv_path, "r") as file:
                                lines = file.readlines()
                            with open(bouquets_tv_path, "w") as file:
                                for line in lines:
                                    if f not in line:
                                        file.write(line)

            self.session.open(MessageBox, f"Deleted {len(self.selected_bouquets)} bouquet(s) successfully!", MessageBox.TYPE_INFO)
            self.selected_bouquets = []
            self.load_iptv_bouquets()
            
            self.session.openWithCallback(
                self.reload_confirm,
                MessageBox,
                "Do you want to reload settings now?",
                MessageBox.TYPE_YESNO
            )
        except Exception as e:
            self.session.open(MessageBox, f"Error deleting bouquets: {str(e)}", MessageBox.TYPE_ERROR)

    def reload_confirm(self, result):
        if result:
            self.reload_settings()

    def reload_settings(self):
        try:
            eDVBDB.getInstance().reloadServicelist()
            eDVBDB.getInstance().reloadBouquets()
            self.session.open(
                MessageBox,
                "Reload successful! Settings updated.",
                MessageBox.TYPE_INFO,
                timeout=5
            )
        except Exception as e:
            self.session.open(
                MessageBox,
                "Reload failed: " + str(e),
                MessageBox.TYPE_ERROR,
                timeout=5
            )

    def up(self):
        self["channel_list"].up()

    def down(self):
        self["channel_list"].down()

    def exit(self):
        self.close()

# Keeping existing BouquetCleaner and main/Plugins functions unchanged
# ... (BouquetCleaner class remains as is)
# ... (main and Plugins functions remain as is)

def main(session, **kwargs):
    session.open(CiefpIPTV)

def Plugins(**kwargs):
    return PluginDescriptor(
        name=f"{PLUGIN_NAME} v{PLUGIN_VERSION}",
        description=PLUGIN_DESCRIPTION,
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="icon.png",
        fnc=main
    )