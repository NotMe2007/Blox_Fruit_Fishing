"""SendInput regressions with mocked OS calls; never emits desktop input."""
import ctypes
from unittest.mock import Mock
import pytest
from Logic.BackGround_Logic import Virtual_Mouse as vm


@pytest.fixture
def mouse(monkeypatch):
    result = vm.VirtualMouse.__new__(vm.VirtualMouse)
    result.user32 = Mock()
    result.user32.SendInput.return_value = 1
    result.user32.GetSystemMetrics.side_effect = lambda i: {76:-1920,77:0,78:3840,79:1080}[i]
    monkeypatch.setattr(result, "_target_ready", lambda x,y: True)
    monkeypatch.setattr(vm.time, "sleep", lambda duration: None)
    return result


def test_input_layout_matches_windows_abi():
    assert ctypes.sizeof(vm.INPUT) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
    assert ctypes.sizeof(vm.MOUSEINPUT) == (32 if ctypes.sizeof(ctypes.c_void_p) == 8 else 24)


@pytest.mark.parametrize("x", [-1920,-1500,0,1919])
def test_press_uses_sendinput_with_virtual_desktop(mouse,x):
    assert mouse.mouse_down(x,100)
    count,buffer,size = mouse.user32.SendInput.call_args.args
    assert count == 1 and size == ctypes.sizeof(vm.INPUT)
    event = buffer[0].mi
    assert event.dx == min(65535,int((x+1920+0.5)*65536/3840))
    assert event.dwFlags == (vm.MOUSEEVENTF_MOVE | vm.MOUSEEVENTF_ABSOLUTE |
                             vm.MOUSEEVENTF_VIRTUALDESK | vm.MOUSEEVENTF_LEFTDOWN)
    mouse.user32.mouse_event.assert_not_called()


def test_zero_accepted_is_failure(mouse):
    mouse.user32.SendInput.return_value = 0
    assert mouse.mouse_down(0,100) is False
    assert mouse.mouse_up(0,100) is False


def test_release_ignores_focus_and_does_not_move(mouse,monkeypatch):
    monkeypatch.setattr(mouse,"_target_ready",lambda x,y: False)
    assert mouse.mouse_down(0,100) is False
    mouse.user32.SendInput.assert_not_called()
    assert mouse.mouse_up(0,100)
    event = mouse.user32.SendInput.call_args.args[1][0].mi
    assert event.dwFlags == vm.MOUSEEVENTF_LEFTUP
    assert event.dx == event.dy == 0


def test_click_releases_after_interruption(mouse,monkeypatch):
    def interrupt(duration):
        if duration == 0.05:
            raise KeyboardInterrupt
    monkeypatch.setattr(vm.time,"sleep",interrupt)
    with pytest.raises(KeyboardInterrupt):
        mouse.click_at(0,100)
    assert mouse.user32.SendInput.call_count == 2
    assert mouse.user32.SendInput.call_args.args[1][0].mi.dwFlags == vm.MOUSEEVENTF_LEFTUP


def test_click_reports_failed_release(mouse):
    mouse.user32.SendInput.side_effect = [1,0]
    assert mouse.click_at(0,100) is False


def test_failed_press_does_not_hold(mouse):
    mouse.user32.SendInput.return_value = 0
    assert mouse.click_at(0,100) is False
    assert mouse.user32.SendInput.call_count == 1


def test_old_entry_point_routes_to_sendinput(mouse,monkeypatch):
    post = Mock()
    monkeypatch.setattr(vm.win32gui,"PostMessage",post)
    assert mouse.ultimate_stealth_click(0,100)
    assert mouse.user32.SendInput.call_count == 2
    post.assert_not_called()


@pytest.mark.parametrize("foreground,point,expected",[(123,(10,10),True),
    (999,(10,10),False),(123,(-1,10),False),(123,(500,10),False)])
def test_target_guard(monkeypatch,foreground,point,expected):
    mouse = vm.VirtualMouse.__new__(vm.VirtualMouse)
    monkeypatch.setattr(mouse,"_resolve_window_manager",lambda: True)
    mouse._get_hwnd_func = lambda: 123
    monkeypatch.setattr(vm.win32gui,"GetForegroundWindow",lambda: foreground)
    monkeypatch.setattr(vm.win32gui,"IsIconic",lambda h: False)
    monkeypatch.setattr(vm.win32gui,"ScreenToClient",lambda h,p: point)
    monkeypatch.setattr(vm.win32gui,"GetClientRect",lambda h: (0,0,500,500))
    assert mouse._target_ready(10,10) is expected


def test_cast_propagates_backend_failure(monkeypatch):
    from Logic import fishing_Script as fishing
    monkeypatch.setattr(fishing,"ISROBLOX_OPEN_AVAILABLE",True)
    monkeypatch.setattr(fishing,"IsRobloxOpen",Mock(validate_roblox_and_game=lambda: True))
    monkeypatch.setattr(fishing,"WINDOW_MANAGER_AVAILABLE",True)
    monkeypatch.setattr(fishing,"ensure_roblox_focused",lambda: True)
    monkeypatch.setattr(fishing,"get_roblox_coordinates",lambda: (400,300))
    monkeypatch.setattr(fishing,"is_virtual_mouse_available",lambda: True)
    backend = Mock()
    backend.cast_hold.return_value = False
    monkeypatch.setattr(fishing,"virtual_mouse",backend)
    assert fishing.CastFishingRod(400,300) is False
    assert backend.cast_hold.call_args.args == (400,300,0.93)
    assert callable(backend.cast_hold.call_args.kwargs["observe"])


def test_cast_sends_button_only_after_positioning(mouse,monkeypatch):
    sequence=[]
    mouse.user32.SetCursorPos.side_effect=lambda x,y: sequence.append(('move',x,y)) or 1
    mouse.user32.GetAsyncKeyState.return_value=0x8000
    def send(count,buffer,size):
        event=buffer[0].mi
        sequence.append(('input',event.dwFlags,event.dx,event.dy))
        return 1
    mouse.user32.SendInput.side_effect=send
    monkeypatch.setattr(vm.time,'sleep',lambda t: sequence.append(('wait',t)))
    assert mouse.cast_hold(100,200,0.93)
    down_index = sequence.index(('input',vm.MOUSEEVENTF_LEFTDOWN,0,0))
    moves = [item for item in sequence[:down_index] if item[0] == 'move']
    assert len(moves) >= 8
    assert moves[0][1:] != (100,200)
    assert moves[-1] == ('move',100,200)
    assert sequence[down_index-1] == ('wait',0.15)
    assert sequence[-1] == ('input',vm.MOUSEEVENTF_LEFTUP,0,0)
    assert all(item[0] != 'move' for item in sequence[down_index:])


def test_cast_missing_held_state_is_failure(mouse):
    mouse.user32.GetAsyncKeyState.return_value=0
    assert not mouse.cast_hold(100,200)
    assert mouse.user32.SendInput.call_args.args[1][0].mi.dwFlags == vm.MOUSEEVENTF_LEFTUP


def test_cast_release_on_interruption(mouse,monkeypatch):
    def sleep(t):
        if t == 0.03:
            raise KeyboardInterrupt
    monkeypatch.setattr(vm.time,'sleep',sleep)
    with pytest.raises(KeyboardInterrupt):
        mouse.cast_hold(100,200)
    assert mouse.user32.SendInput.call_args.args[1][0].mi.dwFlags == vm.MOUSEEVENTF_LEFTUP


def test_cast_failed_position_never_presses(mouse):
    mouse.user32.SetCursorPos.return_value=0
    assert not mouse.cast_hold(100,200)
    assert mouse.user32.SendInput.call_count == 1  # Only the initial release


def test_hotbar_click_glides_then_presses_without_moving(mouse):
    assert mouse.click_at(100,200)
    moves=mouse.user32.SetCursorPos.call_args_list
    assert len(moves) >= 8
    assert moves[0].args != (100,200)
    assert moves[-1].args == (100,200)
    down=mouse.user32.SendInput.call_args_list[0].args[1][0].mi
    assert down.dwFlags == vm.MOUSEEVENTF_LEFTDOWN
    assert down.dx == down.dy == 0


def test_movement_failure_prevents_click(mouse):
    mouse.user32.SetCursorPos.return_value=0
    assert not mouse.click_at(100,200)
    mouse.user32.SendInput.assert_not_called()


def test_focus_loss_after_glide_prevents_press(mouse,monkeypatch):
    monkeypatch.setattr(mouse,'_target_ready',Mock(side_effect=[True,False]))
    assert not mouse.click_at(100,200)
    mouse.user32.SendInput.assert_not_called()
