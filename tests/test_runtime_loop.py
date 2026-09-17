"""Drive the actual runtime loop with a simulated clock and game observations."""
from unittest.mock import Mock
import pytest
from Logic import fishing_Script as fishing
from Logic.BackGround_Logic import Fishing_Rod_Detector as rod


@pytest.fixture
def runtime(monkeypatch):
    now=[100.0]
    monkeypatch.setattr(fishing.time,'time',lambda: now[0])
    monkeypatch.setattr(fishing.time,'sleep',lambda duration: now.__setitem__(0,now[0]+duration))
    monkeypatch.setattr(fishing,'camera_initialized',True)
    monkeypatch.setattr(fishing,'FISHING_ROD_DETECTOR_AVAILABLE',True)
    monkeypatch.setattr(fishing,'FISHING_MINIGAME_AVAILABLE',True)
    monkeypatch.setattr(fishing,'FishingMiniGame',Mock())
    monkeypatch.setattr(fishing,'WINDOW_MANAGER_AVAILABLE',True)
    monkeypatch.setattr(fishing,'get_roblox_window_region',lambda: (0,0,1920,1080))
    monkeypatch.setattr(fishing,'get_roblox_coordinates',lambda: (960,520))
    monkeypatch.setattr(fishing,'ISROBLOX_OPEN_AVAILABLE',True)
    monkeypatch.setattr(fishing,'IsRobloxOpen',Mock(validate_roblox_and_game=lambda: True))
    detector=Mock()
    detector.ensure_rod_equipped.return_value=True
    detector.reset_rod.return_value=True
    monkeypatch.setattr(fishing,'FishingRodDetector',detector)
    cast=Mock(return_value=True)
    monkeypatch.setattr(fishing,'CastFishingRod',cast)
    monkeypatch.setattr(fishing,'Fish_On_Hook',lambda x,y: False)
    monkeypatch.setattr(fishing,'Use_Ability_Fishing',lambda x,y: None)
    monkeypatch.setattr(fishing,'Shift_State',lambda x,y: None)
    return detector,cast,now


def test_runtime_waits_full_bite_timeout_before_each_reset(runtime):
    detector,cast,now=runtime
    cast_times=[]
    reset_times=[]
    cast.side_effect=lambda x,y: cast_times.append(now[0]) or True
    detector.reset_rod.side_effect=lambda: reset_times.append(now[0]) or True
    fishing.main_fishing_loop()
    assert len(cast_times) == 3 and len(reset_times) == 2
    assert all(reset_times[i]-cast_times[i] >= 60 for i in range(2))
    detector.ensure_rod_equipped.assert_called_once()
    detector.check_region_and_act.assert_not_called()


def test_runtime_input_failure_never_unequips(runtime):
    detector,cast,now=runtime
    cast.return_value=False
    fishing.main_fishing_loop()
    detector.reset_rod.assert_not_called()
    detector.check_region_and_act.assert_not_called()
    cast.assert_called_once_with(960,520)


def test_equip_confirmation_never_reclicks(monkeypatch):
    mouse=Mock()
    mouse.click_at.return_value=True
    monkeypatch.setattr(rod,'virtual_mouse',mouse)
    monkeypatch.setattr(rod.time,'sleep',lambda t: None)
    states=iter([(False,(100,200)),(False,(100,200)),None,
                 (False,(100,200)),(True,(100,200))])
    monkeypatch.setattr(rod,'inspect_rod',lambda: next(states))
    assert rod.ensure_rod_equipped()
    mouse.click_at.assert_called_once_with(100,200)


def test_equipped_rod_never_clicked(monkeypatch):
    mouse=Mock()
    monkeypatch.setattr(rod,'virtual_mouse',mouse)
    monkeypatch.setattr(rod,'inspect_rod',lambda: (True,(100,200)))
    assert rod.ensure_rod_equipped()
    mouse.click_at.assert_not_called()


def test_missed_meter_does_not_turn_accepted_input_into_reset(monkeypatch):
    monkeypatch.setattr(fishing,'WINDOW_MANAGER_AVAILABLE',True)
    monkeypatch.setattr(fishing,'ensure_roblox_focused',lambda: True)
    monkeypatch.setattr(fishing,'is_virtual_mouse_available',lambda: True)
    monkeypatch.setattr(fishing,'get_roblox_window_region',lambda: None)
    backend=Mock()
    def hold(x,y,duration,observe):
        observe()
        return True
    backend.cast_hold.side_effect=hold
    monkeypatch.setattr(fishing,'virtual_mouse',backend)
    assert fishing.CastFishingRod(960,520)
