import psutil
import win32gui
import win32process
import time
import requests
import json
import re
from typing import Optional, Tuple, Dict, List


class RobloxChecker:
    """Class to check if Roblox is running and what game is being played using both process detection and Roblox API."""
    
    def __init__(self):
        self.roblox_process_name = "RobloxPlayerBeta.exe"
        self.blox_fruits_keywords = [
            "Blox Fruits",
            "blox fruits", 
            "BLOX FRUITS",
            "BloxFruits"
        ]
        # Known Blox Fruits game IDs on Roblox
        self.blox_fruits_game_ids = [
            2753915549,  # Main Blox Fruits game
            4442272183,  # Blox Fruits (alternative/update)
            7449423635   # Blox Fruits (newer version)
        ]
        self.api_cache = {}
        self.cache_timeout = 300  # 5 minutes cache timeout
    
    def is_roblox_running(self) -> bool:
        """Check if Roblox is currently running."""
        try:
            for process in psutil.process_iter(['pid', 'name']):
                if process.info['name'] and process.info['name'].lower() == self.roblox_process_name.lower():
                    return True
            return False
        except Exception as e:
            print(f"Error checking if Roblox is running: {e}")
            return False
    
    def get_roblox_window_title(self) -> Optional[str]:
        """Get the window title of the Roblox window."""
        try:
            def enum_windows_callback(hwnd, results):
                # Get the process ID of the window
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                
                try:
                    # Get the process name
                    process = psutil.Process(pid)
                    if process.name().lower() == self.roblox_process_name.lower():
                        # Get window title
                        window_title = win32gui.GetWindowText(hwnd)
                        if window_title and window_title.strip():
                            results.append(window_title)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            
            # Return the first non-empty window title found
            for title in windows:
                if title and title.strip() and title != "Roblox":
                    return title
            
            return None
            
        except Exception as e:
            print(f"Error getting Roblox window title: {e}")
            return None
    
    def get_game_id_from_window_title(self, window_title: str) -> Optional[int]:
        """Extract game ID from Roblox window title if present."""
        if not window_title:
            return None
        
        # Look for patterns like "Roblox - GameName" or similar
        # Sometimes the game ID appears in the title or we can infer it
        game_id_pattern = r'(\d{10,})'  # Look for long numbers that could be game IDs
        match = re.search(game_id_pattern, window_title)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        
        return None
    
    def get_game_info_from_api(self, game_id: int) -> Optional[Dict]:
        """Get game information from Roblox API."""
        try:
            # Check cache first
            cache_key = f"game_{game_id}"
            current_time = time.time()
            
            if cache_key in self.api_cache:
                cached_data, cache_time = self.api_cache[cache_key]
                if current_time - cache_time < self.cache_timeout:
                    return cached_data
            
            # Make API request - using the correct endpoint for universe info
            url = f"https://games.roblox.com/v1/games/multiget-place-details?placeIds={game_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Extract the first game from the response
                if isinstance(data, list) and len(data) > 0:
                    game_data = data[0]
                    # Cache the result
                    self.api_cache[cache_key] = (game_data, current_time)
                    return game_data
                elif isinstance(data, dict):
                    # Cache the result
                    self.api_cache[cache_key] = (data, current_time)
                    return data
            else:
                print(f"API request failed with status {response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"Error making API request: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing API response: {e}")
            return None
    
    def search_game_by_name(self, game_name: str) -> Optional[Dict]:
        """Search for a game by name using Roblox API."""
        try:
            # Check cache first
            cache_key = f"search_{game_name.lower()}"
            current_time = time.time()
            
            if cache_key in self.api_cache:
                cached_data, cache_time = self.api_cache[cache_key]
                if current_time - cache_time < self.cache_timeout:
                    return cached_data
            
            # Search API endpoint - using catalog search
            url = "https://catalog.roblox.com/v1/search/items"
            params = {
                'category': 'Experiences',
                'keyword': game_name,
                'limit': 10
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Look for exact or close matches
                if 'data' in data:
                    for game in data['data']:
                        if any(keyword.lower() in game.get('name', '').lower() 
                              for keyword in self.blox_fruits_keywords):
                            # Cache the result
                            self.api_cache[cache_key] = (game, current_time)
                            return game
                
                return None
            else:
                print(f"Search API request failed with status {response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"Error making search API request: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing search API response: {e}")
            return None
    
    def is_blox_fruits_game_id(self, game_id: int) -> bool:
        """Check if the given game ID corresponds to Blox Fruits."""
        return game_id in self.blox_fruits_game_ids
    
    def detect_game_via_api(self) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Detect the current game using API methods.
        
        Returns:
            Tuple[bool, Optional[str], Optional[int]]: (is_blox_fruits, game_name, game_id)
        """
        try:
            # First try to get game ID from window title
            window_title = self.get_roblox_window_title()
            if window_title:
                game_id = self.get_game_id_from_window_title(window_title)
                
                if game_id:
                    # Check if it's a known Blox Fruits game ID
                    if self.is_blox_fruits_game_id(game_id):
                        return True, "Blox Fruits", game_id
                    
                    # Get game info from API
                    game_info = self.get_game_info_from_api(game_id)
                    if game_info and 'name' in game_info:
                        game_name = game_info['name']
                        is_blox_fruits = any(keyword.lower() in game_name.lower() 
                                           for keyword in self.blox_fruits_keywords)
                        return is_blox_fruits, game_name, game_id
                
                # Try searching by window title text
                for keyword in self.blox_fruits_keywords:
                    if keyword.lower() in window_title.lower():
                        # Try to find the game via search API
                        game_info = self.search_game_by_name("Blox Fruits")
                        if game_info:
                            return True, game_info.get('name', 'Blox Fruits'), game_info.get('placeId')
                        return True, window_title, None
            
            return False, None, None
            
        except Exception as e:
            print(f"Error in API game detection: {e}")
            return False, None, None
    
    def is_playing_blox_fruits(self) -> Tuple[bool, Optional[str]]:
        """
        Check if the user is playing Blox Fruits using both window title and API methods.
        
        Returns:
            Tuple[bool, Optional[str]]: (is_playing_blox_fruits, current_game_title)
        """
        # First try API detection for more accurate results
        try:
            is_blox_fruits_api, game_name_api, game_id = self.detect_game_via_api()
            if is_blox_fruits_api and game_name_api:
                return True, game_name_api
            elif game_name_api:  # API worked but it's not Blox Fruits
                return False, game_name_api
        except Exception as e:
            print(f"API detection failed, falling back to window title: {e}")
        
        # Fallback to window title detection
        window_title = self.get_roblox_window_title()
        
        if not window_title:
            return False, None
        
        # Check if any Blox Fruits keywords are in the window title
        for keyword in self.blox_fruits_keywords:
            if keyword in window_title:
                return True, window_title
        
        return False, window_title
    
    def check_roblox_status(self) -> dict:
        """
        Comprehensive check of Roblox status using both process detection and API.
        
        Returns:
            dict: Status information including messages for the user
        """
        result = {
            'roblox_running': False,
            'playing_blox_fruits': False,
            'current_game': None,
            'game_id': None,
            'detection_method': None,
            'message': '',
            'can_proceed': False
        }
        
        # Check if Roblox is running
        if not self.is_roblox_running():
            result['message'] = "Please open Roblox before starting the macro."
            return result
        
        result['roblox_running'] = True
        
        # Wait a moment for window title to load
        time.sleep(1)
        
        # Try API detection first for better accuracy
        try:
            is_blox_fruits_api, game_name_api, game_id = self.detect_game_via_api()
            if game_name_api:  # API detection successful
                result['current_game'] = game_name_api
                result['game_id'] = game_id
                result['playing_blox_fruits'] = is_blox_fruits_api
                result['detection_method'] = 'API'
                
                if not is_blox_fruits_api:
                    result['message'] = f"This script is for Blox Fruits, not '{game_name_api}' (ID: {game_id}). Please join Blox Fruits to use this macro."
                    return result
                else:
                    result['can_proceed'] = True
                    result['message'] = f"Great! You're playing {game_name_api} (ID: {game_id}). The macro is ready to start."
                    return result
        except Exception as e:
            print(f"API detection failed: {e}")
        
        # Fallback to window title detection
        is_blox_fruits, current_game = self.is_playing_blox_fruits()
        result['playing_blox_fruits'] = is_blox_fruits
        result['current_game'] = current_game
        result['detection_method'] = 'Window Title'
        
        if not current_game:
            result['message'] = "Please join a game in Roblox before starting the macro."
            return result
        
        if not is_blox_fruits:
            result['message'] = f"This script is for Blox Fruits, not '{current_game}'. Please join Blox Fruits to use this macro."
            return result
        
        # All checks passed
        result['can_proceed'] = True
        result['message'] = f"Great! You're playing Blox Fruits. The macro is ready to start."
        
        return result
    
    def wait_for_blox_fruits(self, timeout: int = 30) -> bool:
        """
        Wait for the user to open Blox Fruits within a timeout period.
        
        Args:
            timeout (int): Maximum time to wait in seconds
            
        Returns:
            bool: True if Blox Fruits is detected, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.check_roblox_status()
            if status['can_proceed']:
                return True
            
            time.sleep(2)  # Check every 2 seconds
        
        return False


def check_roblox_and_game() -> dict:
    """
    Convenience function to check Roblox status.
    
    Returns:
        dict: Status information
    """
    checker = RobloxChecker()
    return checker.check_roblox_status()


def main():
    """Test the Roblox checker functionality."""
    checker = RobloxChecker()
    
    print("Checking Roblox status...")
    status = checker.check_roblox_status()
    
    print(f"Roblox running: {status['roblox_running']}")
    print(f"Playing Blox Fruits: {status['playing_blox_fruits']}")
    print(f"Current game: {status['current_game']}")
    print(f"Can proceed: {status['can_proceed']}")
    print(f"Message: {status['message']}")


if __name__ == "__main__":
    main()