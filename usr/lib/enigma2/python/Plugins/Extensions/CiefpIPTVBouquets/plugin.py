import os
import requests
from Components.Pixmap import Pixmap
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.FileList import FileList
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from enigma import eDVBDB
import re

PLUGIN_VERSION = "1.6" 
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
        self["red_button"] = Label("IPTV Manager")
        self["blue_button"] = Label("Viewer")  # Promenjeno na Viewer
        self["version_info"] = Label(f"Version: {PLUGIN_VERSION}")
        
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.select_item,
            "cancel": self.exit,
            "up": self.up,
            "down": self.down,
            "green": self.select_item,
            "yellow": self.install,
            "red": self.open_iptv_manager,
            "blue": self.open_viewer  # Promenjeno na open_viewer
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
        self["left_list"].down()

    def exit(self):
        self.close()

    def open_iptv_manager(self):
        self.session.open(IPTVManager)

    def open_viewer(self):
        selected = self["left_list"].getCurrent()
        if selected and selected in self.bouquet_files:
            self.session.open(BouquetViewer, self.bouquet_files[selected]["download_url"], selected)
        else:
            self.session.open(MessageBox, "Please select a bouquet to view!", MessageBox.TYPE_ERROR)

class BouquetViewer(Screen):
    skin = """
        <screen name="bouquetviewer" position="center,center" size="1200,800" title="..:: Bouquet Viewer ::..">
            <widget name="channel_list" position="20,20" size="830,700" scrollbarMode="showOnDemand" itemHeight="33" font="Regular;28" />
            <widget name="background" position="850,0" size="350,800" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpIPTVBouquets/background5.png" zPosition="-1" alphatest="on" />
            <widget name="button_red" position="20,740" size="180,40" font="Bold;22" halign="center" backgroundColor="#9F1313" foregroundColor="#000000" />
            <widget name="button_green" position="220,740" size="180,40" font="Bold;22" halign="center" backgroundColor="#1F771F" foregroundColor="#000000" />
        </screen>
    """

    def __init__(self, session, bouquet_url, bouquet_name):
        Screen.__init__(self, session)
        self.session = session
        self.bouquet_url = bouquet_url
        self.bouquet_name = bouquet_name

        self["channel_list"] = MenuList([])
        self["background"] = Pixmap()
        self["button_red"] = Label("Close")
        self["button_green"] = Label("Select")  # Za buduće proširenje, npr. direktna instalacija

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.exit,
            "cancel": self.exit,
            "red": self.exit,
            "green": self.exit  # Može se dodati funkcionalnost kasnije
        }, -1)

        self.onLayoutFinish.append(self.load_channels)

    def load_channels(self):
        try:
            response = requests.get(self.bouquet_url)
            response.raise_for_status()
            content = response.text.splitlines()
            channels = []
            for line in content:
                if line.startswith("#DESCRIPTION"):
                    channels.append(line.replace("#DESCRIPTION", "").strip())
            self["channel_list"].setList(channels if channels else ["No channels found in this bouquet"])
            self.setTitle(f"Bouquet Viewer: {self.bouquet_name}")
        except Exception as e:
            self["channel_list"].setList([f"Error loading channels: {str(e)}"])

    def exit(self):
        self.close()

class IPTVManager(Screen):
    skin = """
        <screen name="iptvmanager" position="center,center" size="1200,800" title="..:: IPTV Manager ::..">
            <widget name="channel_list" position="20,20" size="830,700" scrollbarMode="showOnDemand" itemHeight="33" font="Regular;28" />
            <widget name="background" position="850,0" size="350,800" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpIPTVBouquets/background3.png" zPosition="-1" alphatest="on" />
            <widget name="button_red" position="20,740" size="180,40" font="Bold;22" halign="center" backgroundColor="#9F1313" foregroundColor="#000000" />
            <widget name="button_green" position="220,740" size="180,40" font="Bold;22" halign="center" backgroundColor="#1F771F" foregroundColor="#000000" />
            <widget name="button_yellow" position="420,740" size="180,40" font="Bold;22" halign="center" backgroundColor="#9F9F13" foregroundColor="#000000" />
            <widget name="button_blue" position="620,740" size="180,40" font="Bold;22" halign="center" backgroundColor="#132B9F" foregroundColor="#000000" />
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
        self["button_yellow"] = Label("Cleaner")  # Dodato za Cleaner
        self["button_blue"] = Label("IPTV Editor")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "ok": self.select_bouquet,
            "cancel": self.exit,
            "up": self.up,
            "down": self.down,
            "red": self.delete_selected,
            "green": self.select_bouquet,
            "yellow": self.open_cleaner,  # Dodato za Cleaner
            "blue": self.open_iptv_editor
        }, -1)

        self.onLayoutFinish.append(self.load_iptv_bouquets)

    def load_iptv_bouquets(self):
        self.iptv_files = []
        display_names = []
        bouquets_order = []
        
        bouquets_tv_path = os.path.join(BOUQUET_PATH, "bouquets.tv")
        if os.path.exists(bouquets_tv_path):
            with open(bouquets_tv_path, "r") as f:
                for line in f:
                    if "#SERVICE" in line and "FROM BOUQUET" in line:
                        start = line.find('"') + 1
                        end = line.find('"', start)
                        if start > 0 and end > start:
                            filename = line[start:end]
                            bouquets_order.append(filename)

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

        ordered_files = []
        for filename in bouquets_order:
            if filename in all_files:
                ordered_files.append((filename, all_files[filename]))
                del all_files[filename]
        
        for filename, display_name in all_files.items():
            ordered_files.append((filename, display_name))

        self.iptv_files = [f[0] for f in ordered_files]
        display_names = [f[1] for f in ordered_files]
        
        if not display_names:
            self["channel_list"].setList(["No IPTV bouquets found"])
        else:
            self["channel_list"].setList(display_names)

    def select_bouquet(self):
        current = self["channel_list"].getCurrent()
        if current and current != "No IPTV bouquets found":
            base_current = current.replace(" [SELECTED]", "")
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

                if display_name == base_current:
                    if base_current in self.selected_bouquets:
                        self.selected_bouquets.remove(base_current)
                    else:
                        self.selected_bouquets.append(base_current)
                    break
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

    def open_iptv_editor(self):
        current = self["channel_list"].getCurrent()
        if current and current != "No IPTV bouquets found":
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
                
                if display_name == current:
                    self.session.open(IPTVEditor, bouquet_path, f)
                    break

    def open_cleaner(self):
        self.session.open(BouquetCleaner)

    def up(self):
        self["channel_list"].up()

    def down(self):
        self["channel_list"].down()

    def exit(self):
        self.close()

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

        self["channel_list"] = MenuList([])
        self["background"] = Pixmap()
        self["button_red"] = Label("Delete")
        self["button_green"] = Label("Select All")

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
            self.selected_file = None
            self["channel_list"].setList([f"{f} [SELECTED]" for f in self.del_files])

    def delete_selected(self):
        if not self.del_files:
            self.session.open(MessageBox, "No .del files to delete!", MessageBox.TYPE_INFO)
            return

        to_delete = []
        if self.selected_file:
            to_delete = [self.selected_file]
        else:
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
            self.load_deleted_bouquets()
            self.selected_file = None
        except Exception as e:
            self.session.open(MessageBox, f"Error deleting files: {str(e)}", MessageBox.TYPE_ERROR)

    def up(self):
        self["channel_list"].up()

    def down(self):
        self["channel_list"].down()

    def exit(self):
        self.close()

class IPTVEditor(Screen):
    skin = """
        <screen name="iptveditor" position="center,center" size="1200,800" title="..:: IPTV Editor ::..">
            <widget name="channel_list" position="20,20" size="830,700" scrollbarMode="showOnDemand" itemHeight="33" font="Regular;28" />
            <widget name="background" position="850,0" size="350,800" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpIPTVBouquets/background4.png" zPosition="-1" alphatest="on" />
            <widget name="button_red" position="20,740" size="140,40" font="Bold;22" halign="center" backgroundColor="#9F1313" foregroundColor="#000000" />
            <widget name="button_green" position="170,740" size="140,40" font="Bold;22" halign="center" backgroundColor="#1F771F" foregroundColor="#000000" />
            <widget name="button_yellow" position="320,740" size="140,40" font="Bold;22" halign="center" backgroundColor="#9F9F13" foregroundColor="#000000" />
            <widget name="button_blue" position="470,740" size="140,40" font="Bold;22" halign="center" backgroundColor="#132B9F" foregroundColor="#000000" />
        </screen>
    """

    def __init__(self, session, bouquet_path, filename):
        Screen.__init__(self, session)
        self.session = session
        self.bouquet_path = bouquet_path
        self.filename = filename
        self.channels = []
        self.selected_channels = []
        self.move_mode = False
        self.channel_names = []
        self.original_channels = []
        self.bouquet_name = ""

        self["channel_list"] = MenuList([])
        self["background"] = Pixmap()
        self["button_red"] = Label("Delete")
        self["button_green"] = Label("Save")
        self["button_yellow"] = Label("Move Mode")
        self["button_blue"] = Label("Select Similar")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "ok": self.select_channel,
            "cancel": self.exit,
            "up": self.up,
            "down": self.down,
            "left": self.page_up,
            "right": self.page_down,
            "red": self.delete_selected,
            "green": self.save_changes,
            "yellow": self.toggle_move_mode,
            "blue": self.select_similar
        }, -1)

        self.onLayoutFinish.append(self.load_channels)

    def load_channels(self):
        self.channels = []
        self.channel_names = []
        try:
            with open(self.bouquet_path, "r") as file:
                current_channel = None
                for line in file:
                    line = line.strip()
                    if line.startswith("#NAME"):
                        self.bouquet_name = line.replace("#NAME", "").strip()
                    elif line.startswith("#SERVICE"):
                        if current_channel:
                            self.channels.append(current_channel)
                        current_channel = {"service": line, "description": ""}
                    elif line.startswith("#DESCRIPTION") and current_channel:
                        current_channel["description"] = line.replace("#DESCRIPTION", "").strip()
                
                if current_channel:
                    self.channels.append(current_channel)
            
            self.original_channels = self.channels.copy()
            self.channel_names = [channel["description"] or channel["service"] for channel in self.channels]
            self.update_list()
        except Exception as e:
            self["channel_list"].setList(["Error loading channels"])
            self.session.open(MessageBox, f"Error loading channels: {str(e)}", MessageBox.TYPE_ERROR)

    def update_list(self):
        display_names = []
        for i, channel in enumerate(self.channels):
            name = channel["description"] or channel["service"]
            if i in self.selected_channels:
                if self.move_mode:
                    name = f">> {name}"
                else:
                    name = f"{name} [SELECTED]"
            display_names.append(name)
        self["channel_list"].setList(display_names)
        if self.selected_channels and self.move_mode:
            self["channel_list"].moveToIndex(self.selected_channels[0])

    def select_channel(self):
        current_index = self["channel_list"].getSelectionIndex()
        if current_index < len(self.channels):
            if current_index in self.selected_channels:
                self.selected_channels.remove(current_index)
            else:
                self.selected_channels.append(current_index)
            self.update_list()

    def select_similar(self):
        current_index = self["channel_list"].getSelectionIndex()
        if current_index < 0 or current_index >= len(self.channels):
            return
        current_name = self.channels[current_index]["description"] or self.channels[current_index]["service"]

        if ":" in current_name:
            base_prefix = current_name.split(":")[0] + ":"
            similar_channels = [
                i for i, channel in enumerate(self.channels)
                if (channel["description"] or channel["service"]).startswith(base_prefix)
            ]
            all_selected = all(i in self.selected_channels for i in similar_channels)
            if all_selected and similar_channels:
                self.selected_channels = [i for i in self.selected_channels if i not in similar_channels]
            elif similar_channels:
                self.selected_channels = list(set(self.selected_channels + similar_channels))
            else:
                self.session.open(MessageBox, f"No similar channels found for: {current_name}", MessageBox.TYPE_INFO)
            self.update_list()
            return

        if (match := re.match(r"(.*?)\s+S\d+\s+E\d+", current_name, re.IGNORECASE)):
            base_prefix = match.group(1) + " "
        elif current_name.startswith("24/7 "):
            base_prefix = "24/7 "
        else:
            parts = current_name.split(" ", 2)
            base_prefix = parts[0] + " " if len(parts) > 1 else current_name + " "
            if len(parts) > 2 and parts[1] in ["Premiere", "Series", "Episode", "TV+"]:
                base_prefix = f"{parts[0]} {parts[1]} "

        base_name = base_prefix.rstrip()
        similar_channels = [
            i for i, channel in enumerate(self.channels)
            if (channel["description"] or channel["service"]).startswith(base_prefix) or
               (channel["description"] or channel["service"]) == base_name
        ]
        all_selected = all(i in self.selected_channels for i in similar_channels)
        if all_selected and similar_channels:
            self.selected_channels = [i for i in self.selected_channels if i not in similar_channels]
        elif similar_channels:
            self.selected_channels = list(set(self.selected_channels + similar_channels))
        else:
            self.session.open(MessageBox, f"No similar channels found for: {current_name}", MessageBox.TYPE_INFO)
        self.update_list()

    def toggle_move_mode(self):
        self.move_mode = not self.move_mode
        self["button_yellow"].setText("Move Mode" if not self.move_mode else "Disable Move")
        if not self.move_mode:
            self.selected_channels = []
        self.update_list()

    def up(self):
        if self.move_mode and self.selected_channels:
            self.move_channels(-1)
        else:
            self["channel_list"].up()

    def down(self):
        if self.move_mode and self.selected_channels:
            self.move_channels(1)
        else:
            self["channel_list"].down()

    def page_up(self):
        if self.move_mode and self.selected_channels:
            self.move_channels(-10)
        else:
            self["channel_list"].pageUp()

    def page_down(self):
        if self.move_mode and self.selected_channels:
            self.move_channels(10)
        else:
            self["channel_list"].pageDown()

    def move_channels(self, offset):
        if not self.selected_channels:
            return

        new_channels = self.channels.copy()
        selected_channels = sorted(self.selected_channels)
        moved_channels = [self.channels[i] for i in selected_channels]
        
        for i in sorted(self.selected_channels, reverse=True):
            new_channels.pop(i)
        
        first_index = selected_channels[0]
        new_index = max(0, min(first_index + offset, len(new_channels)))
        
        for i, channel in enumerate(moved_channels):
            new_channels.insert(new_index + i, channel)
        
        self.selected_channels = [new_index + i for i in range(len(moved_channels))]
        self.channels = new_channels
        self.update_list()

    def delete_selected(self):
        if not self.selected_channels:
            self.session.open(MessageBox, "No channels selected for deletion!", MessageBox.TYPE_ERROR)
            return

        self.session.openWithCallback(
            self.delete_confirmed,
            MessageBox,
            f"Delete {len(self.selected_channels)} selected channel(s)?",
            MessageBox.TYPE_YESNO
        )

    def delete_confirmed(self, result):
        if result:
            new_channels = [ch for i, ch in enumerate(self.channels) if i not in self.selected_channels]
            self.channels = new_channels
            self.selected_channels = []
            self.update_list()
            self.session.open(MessageBox, "Channels deleted successfully!", MessageBox.TYPE_INFO)

    def save_changes(self):
        if self.channels == self.original_channels:
            self.session.open(MessageBox, "No changes to save!", MessageBox.TYPE_INFO)
            return

        try:
            with open(self.bouquet_path, "w") as file:
                file.write(f"#NAME {self.bouquet_name}\n")
                for channel in self.channels:
                    file.write(f"{channel['service']}\n")
                    if channel["description"]:
                        file.write(f"#DESCRIPTION {channel['description']}\n")
            
            self.original_channels = self.channels.copy()
            self.session.open(MessageBox, "Changes saved successfully!", MessageBox.TYPE_INFO)
            
            self.session.openWithCallback(
                self.reload_confirm,
                MessageBox,
                "Do you want to reload settings now?",
                MessageBox.TYPE_YESNO
            )
        except Exception as e:
            self.session.open(MessageBox, f"Error saving changes: {str(e)}", MessageBox.TYPE_ERROR)

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

    def exit(self):
        if self.channels != self.original_channels:
            self.session.openWithCallback(
                self.exit_confirmed,
                MessageBox,
                "You have unsaved changes. Exit without saving?",
                MessageBox.TYPE_YESNO
            )
        else:
            self.close()

    def exit_confirmed(self, result):
        if result:
            self.close()

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