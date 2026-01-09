# This is a method from class VideoTagger
def play_video(self):
    if not self.playing or not self.frames_loaded:
        return
        
    self.current_frame += 1
    if self.current_frame >= self.total_frames:
        self.current_frame = 0
        
    self.show_frame()
    self.draw_tag_markers()
    self.root.after(int(1000/self.fps), self.play_video)

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['play_video']
