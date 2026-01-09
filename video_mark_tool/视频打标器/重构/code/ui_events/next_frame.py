# This is a method from class VideoTagger
def next_frame(self):
    if self.current_frame < self.total_frames - 1:
        self.current_frame += 1
        self.show_frame()
        self.draw_tag_markers()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['next_frame']
