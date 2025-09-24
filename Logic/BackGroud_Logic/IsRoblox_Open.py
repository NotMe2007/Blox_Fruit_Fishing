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
    
    def __init__(self, debug=False):
        self.debug = debug  # Control debug output
        self.roblox_process_name = "RobloxPlayerBeta.exe"
        self.blox_fruits_keywords = [
            "Blox Fruits",
            "blox fruits", 
            "BLOX FRUITS",
            "BloxFruits"
        ]
        # Known Blox Fruits game IDs on Roblox
        self.blox_fruits_game_ids = [
            2753915549,  # Sea 1
            4442272183,  # Sea 2
            7449423635   # Sea 3
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
                            # Check if the window is visible
                            if win32gui.IsWindowVisible(hwnd):
                                # Get window rect for debugging
                                try:
                                    rect = win32gui.GetWindowRect(hwnd)
                                    width = rect[2] - rect[0]
                                    height = rect[3] - rect[1]
                                    print(f"DEBUG: Found Roblox window - Title: '{window_title}', Size: {width}x{height}, HWND: {hwnd}")
                                    results.append((window_title, hwnd, width, height))
                                except:
                                    results.append((window_title, hwnd, 0, 0))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            
            print(f"DEBUG: Found {len(windows)} Roblox windows total")
            
            # Filter out common non-game windows and prioritize visible game windows
            filtered_titles = []
            ignore_patterns = [
                'msctfime ui',  # Windows input method
                'default ime',  # Another input method
                'roblox crash',  # Crash handler
                'roblox studio'  # Roblox Studio (not a game)
            ]
            
            # Sort by window size (larger windows first)
            windows.sort(key=lambda w: w[2] * w[3] if len(w) > 3 else 0, reverse=True)
            
            for window_data in windows:
                title = window_data[0]
                hwnd = window_data[1]
                width = window_data[2] if len(window_data) > 2 else 0
                height = window_data[3] if len(window_data) > 3 else 0
                
                title_lower = title.lower().strip()
                print(f"DEBUG: Examining window - '{title}' ({width}x{height})")
                
                # Skip empty titles
                if not title_lower:
                    print(f"DEBUG: Skipping empty title")
                    continue
                
                # Skip ignored patterns
                if any(pattern in title_lower for pattern in ignore_patterns):
                    print(f"DEBUG: Skipping ignored pattern: {title}")
                    continue
                
                # Prioritize titles that look like actual games
                if any(keyword.lower() in title_lower for keyword in self.blox_fruits_keywords):
                    print(f"Found Blox Fruits window: {title}")
                    return title
                
                # Accept substantial windows that might be games
                if width > 400 and height > 300:
                    if title_lower != 'roblox':  # Non-Roblox titles
                        print(f"DEBUG: Adding substantial window: {title}")
                        filtered_titles.append(title)
                    elif title_lower == 'roblox' and width > 800 and height > 600:
                        # Even plain "Roblox" if it's a large window (likely the game)
                        print(f"DEBUG: Adding large Roblox window: {title}")
                        filtered_titles.append(title)
            
            # Return the first filtered title if no Blox Fruits found
            if filtered_titles:
                selected_title = filtered_titles[0]
                print(f"Selected Roblox window: {selected_title}")
                return selected_title
            
            print("DEBUG: No suitable Roblox windows found")
            return None
            
        except Exception as e:
            print(f"Error getting Roblox window title: {e}")
            return None
    
    def find_active_roblox_window(self) -> Optional[str]:
        """Find the active Roblox window more aggressively."""
        try:
            import win32con
            
            def enum_callback(hwnd, results):
                try:
                    # Check if window is visible and not minimized
                    if not win32gui.IsWindowVisible(hwnd):
                        return True
                    
                    # Get window class and title
                    class_name = win32gui.GetClassName(hwnd)
                    window_title = win32gui.GetWindowText(hwnd)
                    
                    # Get process ID
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    
                    try:
                        process = psutil.Process(pid)
                        if process.name().lower() == self.roblox_process_name.lower():
                            # Check if this looks like a game window
                            if (window_title and 
                                len(window_title.strip()) > 3 and 
                                window_title.strip().lower() not in ['roblox', 'msctfime ui', 'default ime']):
                                
                                # Get window rect to check if it's a substantial window
                                try:
                                    rect = win32gui.GetWindowRect(hwnd)
                                    width = rect[2] - rect[0]
                                    height = rect[3] - rect[1]
                                    
                                    # Only consider windows with substantial size (likely game windows)
                                    if width > 400 and height > 300:
                                        results.append({
                                            'title': window_title,
                                            'hwnd': hwnd,
                                            'class': class_name,
                                            'size': (width, height)
                                        })
                                except:
                                    pass
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                        
                except Exception:
                    pass
                    
                return True
            
            windows = []
            win32gui.EnumWindows(enum_callback, windows)
            
            # Sort by window size (larger windows are more likely to be the game)
            windows.sort(key=lambda w: w['size'][0] * w['size'][1], reverse=True)
            
            # Look for Blox Fruits first
            for window in windows:
                title = window['title']
                if any(keyword.lower() in title.lower() for keyword in self.blox_fruits_keywords):
                    print(f"Found Blox Fruits window: {title} (size: {window['size']})")
                    return title
            
            # Return the largest window if no Blox Fruits found
            if windows:
                largest = windows[0]
                print(f"Found largest Roblox window: {largest['title']} (size: {largest['size']})")
                return largest['title']
            
            return None
            
        except Exception as e:
            print(f"Error in active window search: {e}")
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
    
    def get_roblox_process_info(self) -> Optional[Dict]:
        """Get detailed information about the Roblox process."""
        try:
            roblox_processes = []
            for process in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd']):
                if process.info['name'] and process.info['name'].lower() == self.roblox_process_name.lower():
                    try:
                        # Get command line arguments which might contain game info
                        cmdline = process.info.get('cmdline', [])
                        if self.debug:
                            print(f"DEBUG: Found Roblox process PID {process.info['pid']}")
                            print(f"DEBUG: Command line: {cmdline}")
                        
                        # Look for game ID in command line arguments
                        for arg in cmdline:
                            if isinstance(arg, str):
                                if self.debug:
                                    print(f"DEBUG: Checking arg: {arg}")
                                
                                # Look for URL-encoded placeId parameter (most reliable)
                                if 'placeid%3d' in arg.lower() or 'placeid=' in arg.lower():
                                    # Handle URL encoded version
                                    match = re.search(r'placeid%3d(\d+)', arg, re.IGNORECASE)
                                    if match:
                                        game_id = int(match.group(1))
                                        if self.debug:
                                            print(f"DEBUG: Found game ID from URL-encoded placeId: {game_id}")
                                        return {'game_id': game_id, 'source': 'cmdline_encoded'}
                                    
                                    # Handle normal version
                                    match = re.search(r'placeid=(\d+)', arg, re.IGNORECASE)
                                    if match:
                                        game_id = int(match.group(1))
                                        print(f"DEBUG: Found game ID from placeId: {game_id}")
                                        return {'game_id': game_id, 'source': 'cmdline'}
                                
                                # Look for game IDs in URLs (direct games/ path)
                                if 'roblox.com' in arg and 'games/' in arg:
                                    match = re.search(r'games/(\d+)', arg)
                                    if match:
                                        game_id = int(match.group(1))
                                        print(f"DEBUG: Found game ID from URL: {game_id}")
                                        return {'game_id': game_id, 'source': 'url'}
                                
                                # Look for specific Blox Fruits game IDs in the command line
                                for bf_id in self.blox_fruits_game_ids:
                                    if str(bf_id) in arg:
                                        print(f"DEBUG: Found known Blox Fruits game ID: {bf_id}")
                                        return {'game_id': bf_id, 'source': 'known_id'}
                        
                        roblox_processes.append({'process_info': process.info, 'source': 'process'})
                    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        print(f"DEBUG: Process access error: {e}")
                        continue
            
            if roblox_processes:
                print(f"DEBUG: Found {len(roblox_processes)} Roblox processes but no game ID")
                return roblox_processes[0]  # Return the first one
            
            return None
        except Exception as e:
            print(f"Error getting Roblox process info: {e}")
            return None
    
    def detect_game_from_known_titles(self, window_title: str) -> Optional[Tuple[bool, str, Optional[int]]]:
        """Detect if the game is Blox Fruits based on known window title patterns."""
        if not window_title:
            return None
        
        print(f"DEBUG: Checking window title for Blox Fruits patterns: '{window_title}'")
        
        # Common Blox Fruits window title patterns
        blox_fruits_patterns = {
            r'.*blox.*fruit.*': 2753915549,  # Main game ID
            r'.*fruit.*blox.*': 2753915549,
            r'roblox.*blox.*fruit.*': 2753915549,
            r'.*bloxfruits.*': 2753915549,
        }
        
        title_lower = window_title.lower()
        
        for pattern, game_id in blox_fruits_patterns.items():
            if re.search(pattern, title_lower):  # Changed from match to search
                print(f"DEBUG: Found Blox Fruits pattern '{pattern}' in title")
                return True, "Blox Fruits", game_id
        
        # Check for exact keyword matches
        for keyword in self.blox_fruits_keywords:
            if keyword.lower() in title_lower:
                print(f"DEBUG: Found Blox Fruits keyword '{keyword}' in title")
                return True, "Blox Fruits", 2753915549  # Default to main game ID
        
        # Special case: if title is just "Roblox", it might still be Blox Fruits
        if title_lower.strip() == 'roblox':
            print(f"DEBUG: Found generic 'Roblox' title - could be Blox Fruits")
            return None  # Return None to continue checking
        
        print(f"DEBUG: No Blox Fruits patterns found in title")
        return False, window_title, None
    
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
            
            # Try multiple API endpoints for better success rate
            endpoints = [
                f"https://games.roblox.com/v1/games/multiget-place-details?placeIds={game_id}",
                f"https://games.roblox.com/v1/games/{game_id}",
                f"https://api.roblox.com/universes/get-universe-containing-place?placeid={game_id}"
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            for url in endpoints:
                try:
                    response = requests.get(url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Handle different response formats
                        if isinstance(data, list) and len(data) > 0:
                            game_data = data[0]
                        elif isinstance(data, dict):
                            game_data = data
                        else:
                            continue
                        
                        # Cache the result
                        self.api_cache[cache_key] = (game_data, current_time)
                        return game_data
                except requests.RequestException:
                    continue
            
            print(f"All API endpoints failed for game ID {game_id}")
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
            
            # Try multiple search endpoints
            search_endpoints = [
                {
                    'url': "https://games.roblox.com/v1/games/list",
                    'params': {'model.keyword': game_name, 'model.maxRows': 10}
                },
                {
                    'url': "https://catalog.roblox.com/v1/search/items",
                    'params': {'category': 'Experiences', 'keyword': game_name, 'limit': 10}
                }
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json'
            }
            
            for endpoint in search_endpoints:
                try:
                    response = requests.get(endpoint['url'], params=endpoint['params'], headers=headers, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Look for games in different response structures
                        games = []
                        if 'data' in data:
                            games = data['data']
                        elif 'games' in data:
                            games = data['games']
                        elif isinstance(data, list):
                            games = data
                        
                        # Look for Blox Fruits matches
                        for game in games:
                            game_name_field = game.get('name', game.get('title', ''))
                            if any(keyword.lower() in game_name_field.lower() 
                                  for keyword in self.blox_fruits_keywords):
                                # Cache the result
                                self.api_cache[cache_key] = (game, current_time)
                                return game
                        
                except requests.RequestException:
                    continue
            
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
        Detect the current game using multiple methods including API.
        
        Returns:
            Tuple[bool, Optional[str], Optional[int]]: (is_blox_fruits, game_name, game_id)
        """
        try:
            # Check if we have a recent cached result to avoid spam
            cache_key = "game_detection"
            current_time = time.time()
            if cache_key in self.api_cache:
                cached_result, cache_time = self.api_cache[cache_key]
                if current_time - cache_time < 15.0:  # Use cache for 15 seconds
                    if self.debug and int(current_time) % 10 == 0:  # Only print occasionally
                        print("DEBUG: Using cached game detection result")
                    return cached_result
            
            if self.debug and int(current_time) % 30 == 0:  # Only print every 30 seconds
                print("DEBUG: Starting comprehensive game detection...")
            
            # Method 1: Try to get game ID from Roblox process command line  
            if self.debug and int(current_time) % 30 == 0:  # Reduce debug spam
                print("DEBUG: Checking process command line...")
            process_info = self.get_roblox_process_info()
            if process_info and 'game_id' in process_info:
                game_id = process_info['game_id']
                print(f"Found game ID from process: {game_id}")
                
                # Check if it's a known Blox Fruits game ID
                if self.is_blox_fruits_game_id(game_id):
                    result = (True, "Blox Fruits", game_id)
                    self.api_cache[cache_key] = (result, current_time)
                    return result
                
                # Get game info from API
                game_info = self.get_game_info_from_api(game_id)
                if game_info:
                    game_name = game_info.get('name', game_info.get('title', f'Game {game_id}'))
                    is_blox_fruits = any(keyword.lower() in game_name.lower() 
                                       for keyword in self.blox_fruits_keywords)
                    return is_blox_fruits, game_name, game_id
                else:
                    # API failed - check if this is a known Blox Fruits ID anyway
                    if self.is_blox_fruits_game_id(game_id):
                        print(f"✅ API failed but {game_id} is known Blox Fruits ID - assuming Blox Fruits")
                        result = (True, "Blox Fruits (Known ID)", game_id)
                        self.api_cache[cache_key] = (result, current_time)
                        return result
                    else:
                        print(f"⚠️ API failed for unknown game ID {game_id} - continuing detection...")
            
            # Method 2: Check window title for patterns and game ID
            if self.debug and int(current_time) % 30 == 0:  # Reduce debug spam
                print("DEBUG: Checking window titles...")
            window_title = self.get_roblox_window_title()
            
            # If no window found with basic method, try aggressive search
            if not window_title:
                if self.debug and int(current_time) % 30 == 0:  # Reduce debug spam
                    print("DEBUG: No window found with basic method, trying aggressive search...")
                window_title = self.find_active_roblox_window()
            
            if window_title:
                print(f"DEBUG: Working with window title: '{window_title}'")
                
                # First check against known Blox Fruits patterns
                title_detection = self.detect_game_from_known_titles(window_title)
                if title_detection:
                    is_bf, game_name, game_id = title_detection
                    if is_bf:
                        print(f"Detected Blox Fruits from window title: {window_title}")
                        return True, game_name, game_id
                
                # Try to extract game ID from window title
                game_id = self.get_game_id_from_window_title(window_title)
                if game_id:
                    print(f"Found game ID from window title: {game_id}")
                    
                    # Check if it's a known Blox Fruits game ID
                    if self.is_blox_fruits_game_id(game_id):
                        return True, "Blox Fruits", game_id
                    
                    # Get game info from API
                    game_info = self.get_game_info_from_api(game_id)
                    if game_info:
                        game_name = game_info.get('name', game_info.get('title', f'Game {game_id}'))
                        is_blox_fruits = any(keyword.lower() in game_name.lower() 
                                           for keyword in self.blox_fruits_keywords)
                        return is_blox_fruits, game_name, game_id
                    else:
                        # API failed - for unknown game IDs, continue to other detection methods
                        print(f"⚠️ API failed for game ID {game_id} from window title - continuing detection...")
            
            # Method 3: If no game ID found, try API search based on window title
            if window_title:
                print("DEBUG: Checking for Blox Fruits keywords in title...")
                for keyword in self.blox_fruits_keywords:
                    if keyword.lower() in window_title.lower():
                        print(f"Found Blox Fruits keyword '{keyword}' in window title")
                        # Try to find the game via search API
                        game_info = self.search_game_by_name("Blox Fruits")
                        if game_info:
                            game_name = game_info.get('name', game_info.get('title', 'Blox Fruits'))
                            game_id = game_info.get('placeId', game_info.get('id'))
                            return True, game_name, game_id
                        return True, "Blox Fruits", 2753915549  # Default main game ID
            
            # Method 4: Fallback - if we have a "Roblox" window, assume it might be Blox Fruits
            if window_title and window_title.lower().strip() == 'roblox':
                print("DEBUG: Found generic 'Roblox' window - assuming Blox Fruits (skipping API due to update)")
                # Skip API calls since they're failing after Roblox update - just assume it's Blox Fruits
                result = (True, "Blox Fruits (Generic Window)", 2753915549)
                self.api_cache[cache_key] = (result, current_time)
                return result
            
            # Method 5: Return window title info even if not Blox Fruits
            if window_title and window_title not in ['MSCTFIME UI']:
                print(f"Detected non-Blox Fruits game: {window_title}")
                return False, window_title, None
            
            if self.debug and int(current_time) % 30 == 0:  # Reduce debug spam
                print("DEBUG: No game detected")
            result = (False, None, None)
            self.api_cache[cache_key] = (result, current_time)
            return result
            
        except Exception as e:
            print(f"Error in comprehensive game detection: {e}")
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


def find_roblox_window():
    """Find the Roblox window handle and title."""
    import win32gui
    import win32con
    
    roblox_windows = []
    
    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            window_title = win32gui.GetWindowText(hwnd).lower()
            if 'roblox' in window_title:
                results.append((hwnd, win32gui.GetWindowText(hwnd)))
        return True
    
    win32gui.EnumWindows(enum_callback, roblox_windows)
    return roblox_windows


def bring_roblox_to_front():
    """Find and bring Roblox window to the foreground using multiple methods."""
    import win32gui
    import win32con
    import time
    
    # Try using window manager if available
    try:
        from . import WindowManager
        if hasattr(WindowManager, 'ensure_roblox_focused'):
            return WindowManager.ensure_roblox_focused()
    except ImportError:
        pass
    
    # Fallback to original method
    roblox_windows = find_roblox_window()
    
    if not roblox_windows:
        return False
    
    # Use the first Roblox window found
    hwnd, title = roblox_windows[0]
    
    try:
        # Method 1: Try standard Windows API
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.2)
        
        # Try multiple methods to bring window to front
        success = False
        
        try:
            win32gui.SetForegroundWindow(hwnd)
            success = True
        except Exception as e:
            pass
        
        if not success:
            try:
                # Alternative method: Use ShowWindow
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.BringWindowToTop(hwnd)
                success = True
            except Exception as e:
                pass
        
        if not success:
            try:
                # Method 3: Try VirtualMouse if available
                from . import VirtualMouse
                if hasattr(VirtualMouse, 'virtual_mouse'):
                    virtual_mouse = VirtualMouse.virtual_mouse
                    rect = win32gui.GetWindowRect(hwnd)
                    center_x = (rect[0] + rect[2]) // 2
                    center_y = (rect[1] + rect[3]) // 2
                    
                    # Click on window center to focus it
                    virtual_mouse.click_at(center_x, center_y)
                    time.sleep(0.5)
                    success = True
            except Exception as e:
                pass
        
        if success:
            time.sleep(0.5)  # Give window time to come to front
            return True
        else:
            return False
    
    except Exception as e:
        return False


def validate_roblox_and_game():
    """Check if Roblox is running, in foreground, and playing Blox Fruits.
    Enhanced for Roblox update - more forgiving when API endpoints fail.
    """
    import win32gui
    
    try:
        checker = RobloxChecker()
        
        # Check if Roblox is running
        if not checker.is_roblox_running():
            print("ERROR: Roblox is not running!")
            return False
        
        # Try API detection, but allow graceful fallback if APIs fail (Roblox update issue)
        try:
            game_result = checker.detect_game_via_api()
            if isinstance(game_result, tuple):
                is_blox, game_name, _ = game_result
                if is_blox:
                    print(f"✅ Confirmed Blox Fruits via API: {game_name}")
                    return True
                else:
                    print(f"⚠️ API says not Blox Fruits: {game_name}")
                    # Continue to fallback validation
            else:
                print("⚠️ API detection failed - using fallback validation")
        except Exception as api_error:
            print(f"⚠️ API detection error: {api_error} - using fallback validation")
        
        # Fallback validation: Just check if Roblox window exists and is focused
        # This is more lenient for when Roblox updates break API detection
        foreground_hwnd = win32gui.GetForegroundWindow()
        foreground_title = win32gui.GetWindowText(foreground_hwnd).lower()
        
        if 'roblox' in foreground_title:
            print("✅ Roblox window detected and focused - assuming Blox Fruits (API fallback)")
            return True
        else:
            print("❌ Roblox window not in foreground")
            return False
        
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False


if __name__ == "__main__":
    main()