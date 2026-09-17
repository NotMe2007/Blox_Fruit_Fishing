"""Offline tests for camera input and equipped-state regressions."""
import ctypes
from unittest.mock import Mock
import pytest
import cv2
import numpy as np
from Logic.BackGround_Logic import Virtual_Keyboard as kb
from Logic.BackGround_Logic import Virtual_Mouse as vm
from Logic.BackGround_Logic import Fishing_Rod_Detector as rod


@pytest.fixture
def keyboard(monkeypatch):
    instance = kb.VirtualKeyboard.__new__(kb.VirtualKeyboard)
    instance.user32 = Mock()
    instance.user32.MapVirtualKeyW.return_value = 0x17
    instance.user32.SendInput.return_value = 1
    monkeypatch.setattr(instance, '_target_ready', lambda: True)
    monkeypatch.setattr(kb.time, 'sleep', lambda t: None)
    return instance


def test_keyboard_and_mouse_share_full_input_union():
    assert kb.INPUT is vm.INPUT
    assert ctypes.sizeof(kb.INPUT) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)


def test_zoom_keys_use_scan_codes(keyboard,monkeypatch):
    post = Mock()
    monkeypatch.setattr(kb.win32gui, 'PostMessage', post)
    events=[]
    def send(count,pointer,size):
        e=ctypes.cast(pointer,ctypes.POINTER(kb.INPUT)).contents.ki
        events.append((e.wVk,e.wScan,e.dwFlags,size))
        return 1
    keyboard.user32.SendInput.side_effect=send
    assert keyboard.key_press('i')
    assert events == [(0,0x17,8,ctypes.sizeof(kb.INPUT)),(0,0x17,10,ctypes.sizeof(kb.INPUT))]
    post.assert_not_called()


def test_extended_key_flag(keyboard):
    keyboard.user32.MapVirtualKeyW.return_value=0xe04d
    event=keyboard._create_keyboard_input(0x27,0)
    assert event.ki.wScan == 0x4d and event.ki.dwFlags == 9


def test_failed_keyboard_send_is_false(keyboard):
    keyboard.user32.SendInput.return_value=0
    assert not keyboard.key_press('i')


def test_key_release_on_interrupt(keyboard,monkeypatch):
    def interrupt(t):
        raise KeyboardInterrupt
    monkeypatch.setattr(kb.time,'sleep',interrupt)
    with pytest.raises(KeyboardInterrupt):
        keyboard.key_press('i')
    assert keyboard.user32.SendInput.call_count == 2


def test_relative_drag_and_release(monkeypatch):
    mouse=vm.VirtualMouse.__new__(vm.VirtualMouse)
    mouse.mouse_down=Mock(return_value=True)
    mouse.mouse_up=Mock(return_value=True)
    mouse._target_ready=Mock(return_value=True)
    events=[]
    mouse._send_input=lambda e: events.append((e.mi.dx,e.mi.dy,e.mi.dwFlags)) or 1
    monkeypatch.setattr(vm.time,'sleep',lambda t: None)
    assert mouse.relative_drag(400,300,0,450,duration=0.1)
    assert sum(e[1] for e in events) == 450
    assert all(e[2] == vm.MOUSEEVENTF_MOVE for e in events)
    mouse.mouse_up.assert_called_once_with(400,300,'right')


def test_equipped_requires_colored_selection():
    eq=cv2.imread(str(rod.EQ_PATH))
    un=cv2.imread(str(rod.UN_PATH))
    assert rod._has_equipped_border(eq,(0,0),(eq.shape[1],eq.shape[0]))
    assert not rod._has_equipped_border(un,(0,0),(un.shape[1],un.shape[0]))
    gray=cv2.cvtColor(cv2.cvtColor(eq,cv2.COLOR_BGR2GRAY),cv2.COLOR_GRAY2BGR)
    assert not rod._has_equipped_border(gray,(0,0),(gray.shape[1],gray.shape[0]))


def test_camera_does_not_ignore_failed_drag(monkeypatch):
    from Logic import fishing_Script as fishing
    monkeypatch.setattr(fishing,'is_virtual_mouse_available',lambda: True)
    monkeypatch.setattr(fishing,'VIRTUAL_KEYBOARD_AVAILABLE',True)
    monkeypatch.setattr(fishing,'ensure_roblox_focused',lambda: True)
    monkeypatch.setattr(fishing,'get_roblox_coordinates',lambda: (400,300))
    mouse=Mock()
    mouse.relative_drag.return_value=False
    keyboard=Mock()
    monkeypatch.setattr(fishing,'virtual_mouse',mouse)
    monkeypatch.setattr(fishing,'virtual_keyboard',keyboard)
    assert not fishing.initialize_camera_setup()
    keyboard.key_press.assert_not_called()
