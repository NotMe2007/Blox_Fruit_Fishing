"""Offline regressions: no live mouse or keyboard input."""
from unittest.mock import Mock
import zipfile
import pytest
import numpy as np
from PIL import Image
import Launcher
from Logic.BackGround_Logic.Display_Utils import hotbar_region
from Logic.BackGround_Logic import Window_Manager as wm
from Logic.BackGround_Logic import Screen_Capture as capture
from Logic.BackGround_Logic import Fishing_Rod_Detector as rod


@pytest.mark.parametrize("client", [(0,0,1920,1080), (100,80,2560,1440),
                                    (-1920,0,1920,1080), (50,100,1280,720)])
def test_hotbar_inside_client(client):
    x,y,w,h = hotbar_region(client)
    left,top,width,height = client
    assert left <= x < x+w <= left+width
    assert top <= y < y+h == top+height
    assert y >= top+height*0.84


def test_client_coordinates_refresh_and_exclude_borders(monkeypatch):
    manager = wm.RobloxWindowManager()
    manager.roblox_hwnd = 123
    monkeypatch.setattr(manager, "is_window_valid", lambda: True)
    monkeypatch.setattr(wm.win32gui, "IsIconic", lambda h: False)
    monkeypatch.setattr(wm.win32gui, "GetClientRect", lambda h: (0,0,2560,1440))
    origin = [108,131]
    monkeypatch.setattr(wm.win32gui, "ClientToScreen", lambda h,p: tuple(origin))
    assert manager.get_window_region() == (108,131,2560,1440)
    origin[:] = [-2500,50]
    assert manager.get_window_region() == (-2500,50,2560,1440)
    monkeypatch.setattr(wm.win32gui, "IsIconic", lambda h: True)
    assert manager.get_window_region() is None


def test_capture_bbox_negative_coordinates(monkeypatch):
    cap = capture.ScreenCapture()
    cap.user32 = Mock()
    cap.user32.GetSystemMetrics.side_effect = lambda i: {76:-1920,77:0,78:4480,79:1440}[i]
    grab = Mock(return_value=Image.new("RGB",(300,100)))
    monkeypatch.setattr(capture.ImageGrab, "grab", grab)
    assert cap.capture_region((-1000,100,300,100)).size == (300,100)
    grab.assert_called_once_with(bbox=(-1000,100,-700,200), all_screens=True)
    assert cap.capture_region((-2000,100,300,100)) is None
    assert cap.capture_region((0,0,0,100)) is None


def test_rod_uses_current_client_region(monkeypatch):
    monkeypatch.setattr(wm, "get_roblox_window_region", lambda: (100,100,2560,1440))
    grab = Mock(return_value=Image.new("RGB",(1536,216)))
    monkeypatch.setattr(capture, "screenshot", grab)
    image,gray,x,y = rod.screen_region_image()
    assert (x,y) == (612,1324)
    grab.assert_called_once_with(region=(612,1324,1536,216))


def test_capture_failure_is_unknown(monkeypatch):
    monkeypatch.setattr(rod, "load_templates", lambda: (None,None))
    monkeypatch.setattr(wm, "get_roblox_window_region", lambda: None)
    assert rod.check_region_and_act() is None


def test_missing_template_raises_exception_not_exit(monkeypatch):
    monkeypatch.setattr(rod.cv2,"imread",lambda p: None)
    with pytest.raises(FileNotFoundError):
        rod.load_templates()


def test_match_accepts_exact_size():
    template = np.random.default_rng(7).integers(0,255,(40,40),dtype=np.uint8)
    score,loc,scale,size = rod.multi_scale_match(template,template,scales=[1])
    assert score > 0.99 and loc == (0,0) and size == (40,40)


@pytest.mark.parametrize("value,expected", [("V0.2.5",(0,2,5)),("v0.2.5",(0,2,5)),
                                              ("0.10.0",(0,10,0)),("unknown",None)])
def test_version_comparison(value,expected):
    assert Launcher.version_key(value) == expected


def test_checkout_skips_update(monkeypatch,tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path/".git").mkdir()
    release = Mock()
    monkeypatch.setattr(Launcher,"get_latest_release",release)
    Launcher.check_for_updates()
    release.assert_not_called()


@pytest.mark.parametrize("local", ["V0.2.5", "v0.2.6"])
def test_update_does_not_repeat_or_downgrade(monkeypatch,tmp_path,local):
    monkeypatch.chdir(tmp_path)
    (tmp_path/"version.txt").write_text(local)
    monkeypatch.setattr(Launcher,"get_latest_release",lambda: {"tag_name":"v0.2.5"})
    download = Mock()
    monkeypatch.setattr(Launcher,"download_release",download)
    Launcher.check_for_updates()
    download.assert_not_called()


def test_extract_ignores_old_update_and_blocks_traversal(tmp_path):
    updates = tmp_path/"updates"
    (updates/"old").mkdir(parents=True)
    archive = tmp_path/"release.zip"
    with zipfile.ZipFile(archive,"w") as z:
        z.writestr("new/Main.py", "# app")
    result = Launcher.extract_archive(archive,updates)
    assert result.name == "new"
    with zipfile.ZipFile(archive,"w") as z:
        z.writestr("../../outside.txt", "bad")
    assert Launcher.extract_archive(archive,updates) is None
    assert not (tmp_path/"outside.txt").exists()


def test_test_release_stamps_actual_version(monkeypatch,tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path/"version.txt").write_text("V0.2.4")
    monkeypatch.setattr(Launcher,"get_latest_release",lambda: {"tag_name":"v0.2.5"})
    def download(tag,destination):
        with zipfile.ZipFile(destination,"w") as z:
            z.writestr("release/Main.py", "# app")
            z.writestr("release/version.txt", "V0.2.4")
        return True
    monkeypatch.setattr(Launcher,"download_release",download)
    monkeypatch.setattr("builtins.input",lambda prompt: "y")
    Launcher.check_for_updates()
    versions = list((tmp_path/"updates").glob("release-*/release/version.txt"))
    assert len(versions) == 1
    assert versions[0].read_text() == "v0.2.5"
    assert (tmp_path/"version.txt").read_text() == "V0.2.4"


@pytest.mark.parametrize("scale", [0.75,1.25,1.5,2.0])
def test_resized_template_found(scale):
    template = rod.load_templates()[0]
    height,width = template.shape
    resized = rod.cv2.resize(template,(int(width*scale),int(height*scale)),
                             interpolation=rod.cv2.INTER_AREA)
    canvas = np.zeros((resized.shape[0]+40,resized.shape[1]+80),dtype=np.uint8)
    canvas[20:20+resized.shape[0],30:30+resized.shape[1]] = resized
    score,loc,found_scale,size = rod.multi_scale_match(canvas,template)
    assert score >= rod.threshold
    assert abs(loc[0]-30) <= 2 and abs(loc[1]-20) <= 2


@pytest.mark.parametrize("target", [(-1500,100),(2500,100)])
def test_mouse_does_not_clamp_to_primary_monitor(target):
    from Logic.BackGround_Logic.Virtual_Mouse import VirtualMouse
    mouse = VirtualMouse.__new__(VirtualMouse)
    mouse.virtual_left,mouse.virtual_top = -1920,0
    mouse.virtual_width,mouse.virtual_height = 5760,1080
    mouse.primary_width,mouse.primary_height = 1920,1080
    mouse.user32 = Mock()
    mouse.move_to(*target)
    mouse.user32.SetCursorPos.assert_called_once_with(*target)


def test_import_helper_does_not_load_fishing_engine():
    import subprocess
    import sys
    result = subprocess.run([sys.executable,"-c",
        "import Logic.BackGround_Logic.Display_Utils; import sys; "
        "assert 'Logic.fishing_Script' not in sys.modules"],capture_output=True)
    assert result.returncode == 0, result.stderr
