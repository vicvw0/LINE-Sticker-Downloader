import os
import re
import requests
import wx
import zipfile

from apnggif import apnggif
from pathlib import Path
from glob import glob

PATTERN = b'\x4E\x45\x54\x53\x43\x41\x50\x45\x32\x2E\x30'
REGEX = re.compile(PATTERN)
SUCCESS_GREEN_RGB = (75, 181, 67)
ERROR_RED_RGB = (255, 51, 51)


class MyFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='LINE Sticker Download')
        self.SetSize((485, 300))
        self.SetMinSize((485, 250))
        self.panel = wx.Panel(self)

        # Static text
        store_link_static = wx.StaticText(self.panel, label="LINE store link:")
        save_to_static = wx.StaticText(self.panel, label="Save To:")
        self.status_static = wx.StaticText(self.panel, label="")

        # TextCtrl box
        self.directory = wx.TextCtrl(self.panel)
        self.line_store_link = wx.TextCtrl(self.panel)

        # Event buttons
        dir_dlg_btn = wx.Button(parent=self.panel, label="Browse")
        dir_dlg_btn.Bind(wx.EVT_BUTTON, self.on_dir)

        save_btn = wx.Button(parent=self.panel, label="Save")
        save_btn.Bind(wx.EVT_BUTTON, self.on_download)

        # FlexGridSizer
        fgs = wx.FlexGridSizer(rows=2, cols=3, vgap=15, hgap=5)
        fgs.AddMany([store_link_static, (self.line_store_link, 0, wx.EXPAND), wx.StaticText(self.panel, label=""),
                    save_to_static, (self.directory, 0, wx.EXPAND), dir_dlg_btn])

        fgs.AddGrowableCol(1, 1)

        # Vertical sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(fgs, flag=wx.ALL | wx.EXPAND, border=20)
        sizer.AddSpacer(20)
        sizer.Add(save_btn, flag=wx.CENTER)
        sizer.AddSpacer(10)
        sizer.Add(self.status_static, flag=wx.CENTER)

        self.panel.SetSizer(sizer)

        self.Show()

# ----------------------------------------------------------------------------------------------------------------------
    def on_dir(self, event):
        """
        Show the DirDialog and print the user's choice to stdout
        """
        dlg = wx.DirDialog(self, "Choose a directory:",
                           style=wx.DD_DEFAULT_STYLE
                           # | wx.DD_DIR_MUST_EXIST
                           # | wx.DD_CHANGE_DIR
                           )

        if dlg.ShowModal() == wx.ID_OK:
            self.directory.SetValue(dlg.GetPath())
        dlg.Destroy()

# ----------------------------------------------------------------------------------------------------------------------
    def on_download(self, event):
        link = self.line_store_link.GetValue()
        dir = self.directory.GetValue()

        try:
            pack_id = re.search(r'\d{3,}', link).group()
        except AttributeError:
            self.status_static.SetForegroundColour(ERROR_RED_RGB)
            self.status_static.SetLabel("⚠ Invalid LINE store link.")
            self.panel.Layout()
            return

        if dir == "":
            self.status_static.SetForegroundColour(ERROR_RED_RGB)
            self.status_static.SetLabel("⚠ Please specify a valid directory.")
            self.panel.Layout()
            return

        zip_path = os.path.join(dir, "{}.zip".format(pack_id))
        folder_path = os.path.join(dir, pack_id)

        # Download sticker pack
        url = 'http://dl.stickershop.line.naver.jp/products/0/0/1/{}/pc/stickers.zip'.format(pack_id)
        url_anim = 'http://dl.stickershop.line.naver.jp/products/0/0/1/{}/pc/stickerpack.zip'.format(pack_id)

        # Check if animated
        r = requests.get(url_anim, allow_redirects=True)
        if r.status_code == 404:
            r = requests.get(url, allow_redirects=True)
            if r.status_code == 404:
                self.status_static.SetForegroundColour(ERROR_RED_RGB)
                self.status_static.SetLabel("⚠ Invalid LINE store link.")
                self.panel.Layout()
                return

            open(zip_path, 'wb').write(r.content)

            # Extract and delete .zip
            with zipfile.ZipFile(zip_path, 'r') as ref:
                ref.extractall(folder_path)
            os.remove(zip_path)

            # Delete metadata and thumbnails
            os.remove(os.path.join(folder_path, 'productinfo.meta'))
            os.remove(os.path.join(folder_path, 'tab_off.png'))
            os.remove(os.path.join(folder_path, 'tab_on.png'))
            for f in glob(os.path.join(folder_path, '*_key*')):
                os.remove(f)
        else:
            try:
                open(zip_path, 'wb').write(r.content)
            except FileNotFoundError:
                self.status_static.SetForegroundColour(ERROR_RED_RGB)
                self.status_static.SetLabel("⚠ Please specify a valid directory.")
                self.panel.Layout()
                return

            with zipfile.ZipFile(zip_path, 'r') as ref:
                ref.extractall(folder_path)
            os.remove(zip_path)

            for each_file in Path(folder_path).glob('*.*'):
                os.remove(each_file)

            subdir = Path(os.path.join(folder_path, 'animation'))

            for each_file in Path(subdir).glob('*.*'):  # grabs all files
                trg_path = each_file.parent.parent  # gets the parent of the folder
                each_file.rename(trg_path.joinpath(each_file.name))  # moves to parent folder.

            os.removedirs(subdir)

            for f in glob(os.path.join(folder_path, '*_key*')):
                os.remove(f)

            for f in glob(os.path.join(folder_path, '*.png')):
                apnggif(f)
                os.remove(f)

            for f in glob(os.path.join(folder_path, '*')):
                a = open(f, 'r+b')
                for match_obj in REGEX.finditer(a.read()):
                    offset = match_obj.start()
                    a.seek(offset + 13)
                    a.write(b'\x00')

        self.status_static.SetForegroundColour(SUCCESS_GREEN_RGB)
        self.status_static.SetLabel("✓ Stickers saved successfully!")
        self.panel.Layout()
        # Done!


if __name__ == '__main__':
    app = wx.App()
    frame = MyFrame()
    app.MainLoop()
