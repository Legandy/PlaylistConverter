# conflict_resolver.py - Handle playlist conflicts and merging
import os
import re
import time
import hashlib
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Set, Tuple, Optional
from enum import Enum

class ConflictResolution(Enum):
    PC_WINS = "pc_wins"
    SMARTPHONE_WINS = "smartphone_wins" 
    MERGE_BOTH = "merge_both"
    MERGE_NO_DUPLICATES = "merge_no_duplicates"
    MANUAL = "manual"
    SKIP = "skip"

@dataclass
class PlaylistEntry:
    """Represents a single playlist entry with metadata"""
    path: str
    normalized_path: str = ""
    file_size: Optional[int] = None
    last_modified: Optional[float] = None
    
    def __post_init__(self):
        if not self.normalized_path:
            self.normalized_path = self.normalize_path(self.path)
    
    @staticmethod
    def normalize_path(path: str) -> str:
        """Normalize path for duplicate detection"""
        # Remove comments and whitespace
        clean_path = path.strip()
        if clean_path.startswith('#'):
            return clean_path
        
        # Normalize separators and case
        normalized = os.path.normpath(clean_path.lower())
        normalized = normalized.replace('\\', '/')
        
        # Extract just filename if full path
        filename = os.path.basename(normalized)
        return filename if filename else normalized
    
    def is_duplicate_of(self, other: 'PlaylistEntry') -> bool:
        """Check if this entry is a duplicate of another"""
        if self.normalized_path.startswith('#') or other.normalized_path.startswith('#'):
            return False  # Don't consider comments as duplicates
            
        return self.normalized_path == other.normalized_path

@dataclass 
class PlaylistConflict:
    """Represents a conflict between two playlist versions"""
    playlist_name: str
    pc_version: List[PlaylistEntry]
    smartphone_version: List[PlaylistEntry]
    pc_modified: float
    smartphone_modified: float
    conflict_type: str
    
    def get_newer_version(self) -> str:
        """Return which version is newer"""
        return "pc" if self.pc_modified > self.smartphone_modified else "smartphone"
    
    def has_meaningful_changes(self) -> bool:
        """Check if the conflict involves actual content changes"""
        pc_content = [e.normalized_path for e in self.pc_version if not e.path.startswith('#')]
        smartphone_content = [e.normalized_path for e in self.smartphone_version if not e.path.startswith('#')]
        
        return set(pc_content) != set(smartphone_content)

class ConflictResolver:
    """Handles playlist conflicts and merging operations"""
    
    def __init__(self, log_func=None):
        self.log_func = log_func or print
        self.conflict_rules = {}  # User-defined rules for specific playlists
        self.default_resolution = ConflictResolution.MERGE_NO_DUPLICATES
    
    def log(self, message: str):
        """Log a message"""
        if self.log_func:
            self.log_func(message)
    
    def parse_playlist_file(self, file_path: str) -> List[PlaylistEntry]:
        """Parse a playlist file into entries"""
        entries = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.rstrip('\n\r')
                    if line:  # Include all non-empty lines (including comments)
                        entries.append(PlaylistEntry(path=line))
        except Exception as e:
            self.log(f"🚨 Error parsing {file_path}: {e}")
            
        return entries
    
    def detect_conflict(self, pc_path: str, smartphone_path: str) -> Optional[PlaylistConflict]:
        """Detect if two playlist versions have a conflict"""
        try:
            # Get file modification times
            pc_mtime = os.path.getmtime(pc_path)
            smartphone_mtime = os.path.getmtime(smartphone_path)
            
            # Parse both versions
            pc_entries = self.parse_playlist_file(pc_path)
            smartphone_entries = self.parse_playlist_file(smartphone_path)
            
            # Create conflict object
            conflict = PlaylistConflict(
                playlist_name=os.path.basename(pc_path),
                pc_version=pc_entries,
                smartphone_version=smartphone_entries,
                pc_modified=pc_mtime,
                smartphone_modified=smartphone_mtime,
                conflict_type="content_change"
            )
            
            # Only return conflict if there are meaningful changes
            if conflict.has_meaningful_changes():
                return conflict
                
        except Exception as e:
            self.log(f"🚨 Error detecting conflict: {e}")
            
        return None
    
    def find_duplicates(self, entries: List[PlaylistEntry]) -> Dict[str, List[int]]:
        """Find duplicate entries in a playlist"""
        duplicates = {}
        
        for i, entry in enumerate(entries):
            if entry.normalized_path.startswith('#'):
                continue  # Skip comments
                
            normalized = entry.normalized_path
            if normalized not in duplicates:
                duplicates[normalized] = []
            duplicates[normalized].append(i)
        
        # Only return entries that have duplicates
        return {k: v for k, v in duplicates.items() if len(v) > 1}
    
    def remove_duplicates(self, entries: List[PlaylistEntry]) -> List[PlaylistEntry]:
        """Remove duplicate entries, keeping the first occurrence"""
        seen = set()
        result = []
        
        for entry in entries:
            if entry.normalized_path.startswith('#'):
                result.append(entry)  # Always keep comments
            elif entry.normalized_path not in seen:
                seen.add(entry.normalized_path)
                result.append(entry)
            # Skip duplicates
                
        return result
    
    def merge_playlists(self, 
                       entries1: List[PlaylistEntry], 
                       entries2: List[PlaylistEntry],
                       remove_duplicates: bool = True) -> List[PlaylistEntry]:
        """Merge two playlist versions"""
        
        # Start with first playlist
        merged = entries1.copy()
        
        # Add entries from second playlist that aren't already present
        existing_paths = {e.normalized_path for e in entries1 if not e.path.startswith('#')}
        
        for entry in entries2:
            if entry.path.startswith('#'):
                # Add comments from second playlist
                merged.append(entry)
            elif not remove_duplicates or entry.normalized_path not in existing_paths:
                merged.append(entry)
                if remove_duplicates:
                    existing_paths.add(entry.normalized_path)
        
        # Remove duplicates if requested
        if remove_duplicates:
            merged = self.remove_duplicates(merged)
            
        return merged
    
    def resolve_conflict(self, 
                        conflict: PlaylistConflict, 
                        resolution: ConflictResolution = None) -> List[PlaylistEntry]:
        """Resolve a playlist conflict using the specified strategy"""
        
        if resolution is None:
            resolution = self.conflict_rules.get(conflict.playlist_name, self.default_resolution)
        
        if resolution == ConflictResolution.PC_WINS:
            self.log(f"🏆 PC version wins for {conflict.playlist_name}")
            return conflict.pc_version
            
        elif resolution == ConflictResolution.SMARTPHONE_WINS:
            self.log(f"📱 Smartphone version wins for {conflict.playlist_name}")
            return conflict.smartphone_version
            
        elif resolution == ConflictResolution.MERGE_BOTH:
            self.log(f"🔀 Merging both versions of {conflict.playlist_name} (with duplicates)")
            return self.merge_playlists(conflict.pc_version, conflict.smartphone_version, remove_duplicates=False)
            
        elif resolution == ConflictResolution.MERGE_NO_DUPLICATES:
            self.log(f"🔀 Merging both versions of {conflict.playlist_name} (no duplicates)")
            return self.merge_playlists(conflict.pc_version, conflict.smartphone_version, remove_duplicates=True)
            
        elif resolution == ConflictResolution.SKIP:
            self.log(f"⏭️ Skipping conflict resolution for {conflict.playlist_name}")
            return None
            
        else:  # MANUAL or unknown
            self.log(f"❓ Manual resolution required for {conflict.playlist_name}")
            return None
    
    def write_resolved_playlist(self, entries: List[PlaylistEntry], output_path: str):
        """Write resolved playlist entries to file"""
        try:
            # Add resolution metadata
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with open(output_path, 'w', encoding='utf-8') as f:
                # Write metadata header
                f.write(f"# Resolved on {timestamp}\n")
                f.write(f"# Merged playlist with conflict resolution\n")
                f.write(f"# Total entries: {len([e for e in entries if not e.path.startswith('#')])}\n")
                
                # Write all entries
                for entry in entries:
                    f.write(entry.path + '\n')
                    
            self.log(f"✅ Resolved playlist written to {output_path}")
            
        except Exception as e:
            self.log(f"🚨 Error writing resolved playlist: {e}")
    
    def analyze_playlist(self, file_path: str) -> Dict:
        """Analyze a playlist and return statistics"""
        entries = self.parse_playlist_file(file_path)
        
        # Separate content from comments
        content_entries = [e for e in entries if not e.path.startswith('#')]
        comment_entries = [e for e in entries if e.path.startswith('#')]
        
        # Find duplicates
        duplicates = self.find_duplicates(entries)
        
        # Calculate statistics
        stats = {
            'total_lines': len(entries),
            'content_entries': len(content_entries),
            'comment_lines': len(comment_entries),
            'duplicate_groups': len(duplicates),
            'duplicate_entries': sum(len(indices) - 1 for indices in duplicates.values()),
            'unique_entries': len(content_entries) - sum(len(indices) - 1 for indices in duplicates.values()),
            'duplicates_detail': duplicates
        }
        
        return stats
    
    def set_conflict_rule(self, playlist_name: str, resolution: ConflictResolution):
        """Set a conflict resolution rule for a specific playlist"""
        self.conflict_rules[playlist_name] = resolution
        self.log(f"⚙️ Set rule for {playlist_name}: {resolution.value}")
    
    def get_conflict_summary(self, conflict: PlaylistConflict) -> str:
        """Generate a human-readable summary of a conflict"""
        pc_count = len([e for e in conflict.pc_version if not e.path.startswith('#')])
        smartphone_count = len([e for e in conflict.smartphone_version if not e.path.startswith('#')])
        
        newer = conflict.get_newer_version()
        time_diff = abs(conflict.pc_modified - conflict.smartphone_modified)
        
        summary = f"""
Conflict in playlist: {conflict.playlist_name}
PC version: {pc_count} songs (modified {datetime.fromtimestamp(conflict.pc_modified).strftime('%Y-%m-%d %H:%M')})
Smartphone version: {smartphone_count} songs (modified {datetime.fromtimestamp(conflict.smartphone_modified).strftime('%Y-%m-%d %H:%M')})
Newer version: {newer.upper()} (by {time_diff:.0f} seconds)
        """.strip()
        
        return summary

# Example usage and integration functions
def integrate_conflict_resolution(existing_sync_function):
    """Decorator to add conflict resolution to existing sync functions"""
    
    def wrapper(*args, **kwargs):
        resolver = ConflictResolver()
        
        # Check for conflicts before syncing
        # This would integrate with your existing conversion.py logic
        
        try:
            return existing_sync_function(*args, **kwargs)
        except Exception as e:
            resolver.log(f"🚨 Sync failed, checking for conflicts: {e}")
            # Handle conflict resolution here
            raise
            
    return wrapper

def demo_conflict_resolution():
    """Demo function showing how conflict resolution works"""
    
    print("🔀 Conflict Resolution Demo")
    print("=" * 50)
    
    resolver = ConflictResolver()
    
    # Create sample playlist entries
    pc_entries = [
        PlaylistEntry("# My Awesome Playlist"),
        PlaylistEntry("Songs/song1.mp3"),
        PlaylistEntry("Songs/song2.mp3"), 
        PlaylistEntry("Songs/song3.mp3"),
    ]
    
    smartphone_entries = [
        PlaylistEntry("# My Awesome Playlist - Modified on Phone"),
        PlaylistEntry("Songs/song1.mp3"),  # Same song
        PlaylistEntry("Songs/song2.mp3"),  # Same song
        PlaylistEntry("Songs/new_song.mp3"),  # New song
    ]
    
    # Create a mock conflict
    conflict = PlaylistConflict(
        playlist_name="MyPlaylist.m3u",
        pc_version=pc_entries,
        smartphone_version=smartphone_entries,
        pc_modified=time.time() - 100,  # PC version older
        smartphone_modified=time.time(),  # Smartphone version newer
        conflict_type="content_change"
    )
    
    print(resolver.get_conflict_summary(conflict))
    print()
    
    # Test different resolution strategies
    strategies = [
        ConflictResolution.PC_WINS,
        ConflictResolution.SMARTPHONE_WINS,
        ConflictResolution.MERGE_NO_DUPLICATES
    ]
    
    for strategy in strategies:
        print(f"Resolution: {strategy.value}")
        resolved = resolver.resolve_conflict(conflict, strategy)
        if resolved:
            print(f"Result: {len([e for e in resolved if not e.path.startswith('#')])} songs")
            for entry in resolved[:5]:  # Show first 5 entries
                print(f"  {entry.path}")
        print()

if __name__ == "__main__":
    demo_conflict_resolution()
