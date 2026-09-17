from pathlib import Path
from unittest.mock import Mock
import cv2
import numpy as np
import pytest
from Logic.BackGround_Logic.Casting_Recovery import has_casting_meter, cast_with_recovery
from Logic.BackGround_Logic import Fishing_Rod_Detector as rod


def test_user_meter_screenshot():
    frame=cv2.imread(str(Path(__file__).parent/'fixtures'/'casting_meter.png'))
    assert has_casting_meter(frame)
    # Same meter embedded in a full-size client screenshot.
    canvas=np.zeros((1080,1920,3),dtype=np.uint8)
    canvas[100:100+frame.shape[0],500:500+frame.shape[1]]=frame
    assert has_casting_meter(canvas)


def test_absent_and_horizontal_green_are_not_casting():
    frame=np.full((720,1280,3),180,dtype=np.uint8)
    assert not has_casting_meter(frame)
    frame[400:420,200:500]=(0,255,0)
    assert not has_casting_meter(frame)
    assert not has_casting_meter(None)


def test_confirmed_cast_never_toggles():
    cast=Mock(return_value=True)
    reset=Mock()
    assert cast_with_recovery(cast,reset)
    reset.assert_not_called()


def test_missing_meter_resets_then_retries():
    cast=Mock(side_effect=[False,True])
    reset=Mock(return_value=True)
    assert cast_with_recovery(cast,reset)
    assert cast.call_count == 2 and reset.call_count == 1


def test_repeated_failure_stops_after_two_resets():
    cast=Mock(return_value=False)
    reset=Mock(return_value=True)
    assert not cast_with_recovery(cast,reset)
    assert cast.call_count == 3 and reset.call_count == 2


def test_failed_reset_never_recasts():
    cast=Mock(return_value=False)
    assert not cast_with_recovery(cast,lambda: False)
    assert cast.call_count == 1


def test_reset_verifies_both_states(monkeypatch):
    mouse=Mock()
    mouse.click_at.return_value=True
    monkeypatch.setattr(rod,'virtual_mouse',mouse)
    monkeypatch.setattr(rod.time,'sleep',lambda t: None)
    monkeypatch.setattr(rod,'inspect_rod',Mock(side_effect=[
        (True,(100,200)),(False,(110,200)),(True,(110,200))]))
    assert rod.reset_rod()
    assert [call.args for call in mouse.click_at.call_args_list] == [(100,200),(110,200)]


def test_reset_stops_if_unequip_not_verified(monkeypatch):
    mouse=Mock()
    mouse.click_at.return_value=True
    monkeypatch.setattr(rod,'virtual_mouse',mouse)
    monkeypatch.setattr(rod.time,'sleep',lambda t: None)
    monkeypatch.setattr(rod,'inspect_rod',lambda: (True,(100,200)))
    assert not rod.reset_rod()
    assert mouse.click_at.call_count == 1


def test_observation_runs_during_hold_and_releases_on_failure(monkeypatch):
    from Logic.BackGround_Logic.Virtual_Mouse import VirtualMouse, MOUSEEVENTF_LEFTDOWN
    mouse=VirtualMouse.__new__(VirtualMouse)
    mouse.user32=Mock()
    mouse.user32.GetAsyncKeyState.return_value=0x8000
    mouse._target_ready=lambda x,y: True
    mouse._send_input=Mock(return_value=1)
    mouse.mouse_up=Mock(return_value=True)
    monkeypatch.setattr(rod.time,'sleep',lambda t: None)
    def observe():
        assert mouse._send_input.call_args.args[0].mi.dwFlags == MOUSEEVENTF_LEFTDOWN
        assert mouse.mouse_up.call_count == 1  # initial reset only
        raise RuntimeError('capture failed')
    with pytest.raises(RuntimeError):
        mouse.cast_hold(100,200,observe=observe)
    assert mouse.mouse_up.call_count == 2
