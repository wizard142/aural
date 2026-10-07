import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import runtime

class PlatformTests(unittest.TestCase):
    def test_windows_data_uses_local_appdata(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(runtime.data_directory('win32',{'LOCALAPPDATA':temp},temp),Path(temp)/'Aural')
    def test_platform_defaults_and_overrides(self):
        home=Path('/test-home')
        self.assertEqual(runtime.data_directory('win32',{},home),home/'AppData/Local/Aural')
        self.assertEqual(runtime.data_directory('linux',{},home),home/'.local/share/aural')
        self.assertEqual(runtime.data_directory('linux',{'XDG_DATA_HOME':'/alternate'},home),Path('/alternate/aural'))
        self.assertEqual(runtime.data_directory('win32',{'AURAL_DATA':'/custom'},home),Path('/custom'))
    def test_bundled_windows_tools_precede_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'vendor/bin';folder.mkdir(parents=True);tool=folder/'ffmpeg.exe';tool.write_bytes(b'test')
            with patch.object(runtime,'APP_ROOT',root),patch.object(runtime.sys,'platform','win32'),patch.dict(os.environ,{},clear=True),patch.object(runtime.shutil,'which') as which:
                self.assertEqual(runtime.binary('ffmpeg'),str(tool));which.assert_not_called()
    def test_frozen_and_source_downloader_commands(self):
        with patch.object(runtime.sys,'frozen',True,create=True):self.assertEqual(runtime.downloader_command(),[sys.executable,'--download-worker'])
        with patch.object(runtime.sys,'frozen',False,create=True),patch.object(runtime.sys,'platform','win32'):
            self.assertEqual(runtime.downloader_command(),[sys.executable,'-m','yt_dlp'])
    def test_windows_child_options(self):
        with patch.object(runtime.sys,'platform','win32'),patch.object(runtime.subprocess,'CREATE_NO_WINDOW',0x08000000,create=True):
            options=runtime.subprocess_options();self.assertEqual(options['creationflags'],0x08000000);self.assertEqual(options['encoding'],'utf-8');self.assertEqual(options['stdin'],runtime.subprocess.DEVNULL)
    def test_missing_override_has_actionable_error(self):
        with patch.dict(os.environ,{'AURAL_FFMPEG':'/does-not-exist.exe'}):
            with self.assertRaises(FileNotFoundError):runtime.binary('ffmpeg')

if __name__=='__main__':unittest.main()
