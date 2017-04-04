import sys, aiohttp, asyncio, os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

__author__ = 'Alan Baumgartner'

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint)
        self.setWindowTitle('Login to Instagram')
        layout = QGridLayout()

        self.username_label = QLabel('Username')
        self.password_label = QLabel('Password')
        self.username_text = QLineEdit()
        self.password_text = QLineEdit()

        buttons = QDialogButtonBox()

        buttons.addButton("Ok", QDialogButtonBox.YesRole)
        buttons.addButton("Skip", QDialogButtonBox.NoRole)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        self.password_text.setEchoMode(2)

        layout.addWidget(self.username_label, 0, 0)
        layout.addWidget(self.password_label, 1, 0)
        layout.addWidget(self.username_text, 0, 1)
        layout.addWidget(self.password_text, 1, 1)

        layout.addWidget(buttons, 2, 0, 3, 0)

        self.setLayout(layout)
        self.setGeometry(400, 400, 300, 60)

    @staticmethod
    def getLoginInfo():
        dialog = LoginDialog()
        result = dialog.exec_()
        return dialog.username_text.text(), dialog.password_text.text(), result == QDialog.Accepted

class ImportDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowTitle('Import usernames')
        layout = QGridLayout()

        self.file_label = QLabel('Filename')
        self.file_text = QLineEdit()

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(self.file_label, 0, 0)
        layout.addWidget(self.file_text, 0, 1)

        layout.addWidget(buttons, 1, 0, 2, 0)

        self.setLayout(layout)
        self.setGeometry(400, 400, 200, 60)

    @staticmethod
    def getFileInfo():
        dialog = ImportDialog()
        result = dialog.exec_()
        return dialog.file_text.text(), result == QDialog.Accepted



class Checker(QThread):

    #Signal Variables.
    pupdate = pyqtSignal(object)
    count = 0

    #Global Variables.
    LOGIN_URL = 'https://www.instagram.com/accounts/login/ajax/'
    URL = 'https://www.instagram.com/{}'

    def __init__(self, igname, igpass, result):
        super().__init__()
        self.igname = igname
        self.igpass = igpass
        self.result = result

    async def download_file(self, username, url, session, sem, lock):
        #Downloads and saves photos/videos
        async with sem:
            try:
                async with session.get(url) as resp:
                    out = await resp.read()
                    filename = url.split('/')[-1]
                    path = username + '/' + filename

                    if not os.path.exists(username):
                        os.makedirs(username)

                    with open(path, 'wb') as f:
                        f.write(out)
            except:
                pass

            finally:
                with await lock:
                    self.count += 1
                self.pupdate.emit(self.count)

    async def getJSON(self, url, session):
        #Gets json response which contains photo/video urls
        async with session.get(url) as resp:
            data = await resp.json()
            return data

    async def main(self):
        #Puts each url in a list for each username
        sem = asyncio.BoundedSemaphore(50)
        lock = asyncio.Lock()
        async with aiohttp.ClientSession() as session:
            if self.result:
                await self.login(self.igname, self.igpass, session)
            try:
                usernames = get_usernames()
                for username in usernames:
                    url = 'http://instagram.com/' + username + '/media/?max_id='
                    urls = []
                    max_id = ''
                    moreDataToFetch = True
                    while(moreDataToFetch):
                        nextUrl = url + max_id
                        jsonData = await self.getJSON(nextUrl, session)
                        moreDataToFetch = jsonData['more_available']
                        for item in jsonData['items']:
                            imgUrl = None
                            max_id = item['id']
                            if item['type'] == 'image':
                                imgUrl = item['images']['standard_resolution']['url']
                            elif item['type'] == 'video':
                                imgUrl = item['videos']['standard_resolution']['url']
                            urls.append(imgUrl)

                    tasks = [self.download_file(username, url, session, sem, lock) for url in urls]
                    await asyncio.gather(*tasks)
            except:
                pass

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.main())
        finally:
            loop.close()


    #Logs into Instagram.
    async def login(self, username, password, session):
        async with session.get(self.URL.format('')) as response:
            csrftoken = await response.text()

        csrftoken = csrftoken.split('csrf_token": "')[1].split('"')[0]

        async with session.post(
                self.LOGIN_URL,
                    headers={
                        'x-csrftoken': csrftoken, 'x-instagram-ajax':'1',
                        'x-requested-with': 'XMLHttpRequest',
                        'Origin': self.URL, 'Referer': self.URL
                        },
                    data={
                        'username':username, 'password':password
                    }
                ) as response:

                text = await response.json()
                if 'authenticated' in text:
                    pass
                else:
                    sys.exit(text)

class App(QMainWindow):
 
    def __init__(self):

        #Declares some constructor variables.
        super().__init__()
        self.title = 'Instagram Username Checker'
        self.left = 300
        self.top = 300
        self.width = 300
        self.height = 400
        self.initUI()

    def initUI(self):

        #Setup layout.
        wid = QWidget(self)
        self.setCentralWidget(wid)
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
 
        layout = QGridLayout()
        wid.setLayout(layout)
 
        #Create Widgets.
        menu_bar = self.menuBar()

        menu = menu_bar.addMenu("File")

        import_action = QAction("Import Usernames", self)
        import_action.triggered.connect(self.import_usernames)

        quit_action = QAction("Close", self)
        quit_action.triggered.connect(self.quit)

        menu.addAction(import_action)
        menu.addAction(quit_action)

        self.start_button = QPushButton('Start')
        self.start_button.clicked.connect(self.start_clicked)

        self.stop_button = QPushButton('Stop')
        self.stop_button.clicked.connect(self.stop_clicked)

        self.input_text = QTextEdit()

        input_label = QLabel('Usernames to download')
        input_label.setAlignment(Qt.AlignCenter)

        self.progress_bar = QProgressBar()
 
        #Add widgets to the window.
        layout.addWidget(input_label, 0, 0, 1, 0)
        layout.addWidget(self.input_text, 1, 0, 1, 2)
        layout.addWidget(self.start_button, 3, 0)
        layout.addWidget(self.stop_button, 3, 1)
        layout.addWidget(self.progress_bar, 4, 0, 5, 0)
		
    #When the start button is clicked, start the checker thread.
    def start_clicked(self):
        login = LoginDialog()
        igname, igpass, result = login.getLoginInfo()
        usernames = get_usernames()
        self.progress_bar.setMaximum(len(usernames))
        self.thread = Checker(igname, igpass, result)
        self.thread.pupdate.connect(self.update_progress)
        self.thread.start()

    #When the stop button is clicked, terminate the checker thread.
    def stop_clicked(self):
        try:
            self.thread.terminate()
        except:
            pass
 
    #When the checker thread emits a signal, update the progress bar.
    def update_progress(self, val):
        self.progress_bar.setValue(val)

    def import_usernames(self):
        importDialog = ImportDialog()
        filename, result = importDialog.getFileInfo()
        if result:
            try:
                with open(filename, "r") as f:
                    out = f.read()
                    self.input_text.setText(out)
            except:
                pass
        else:
            pass

    def quit(self):
        sys.exit()

if __name__ == '__main__':

    #Get usernames from the input textbox.
    def get_usernames():
        proxies = window.input_text.toPlainText()
        proxies = proxies.strip()
        proxies = proxies.split('\n')
        return proxies

    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())