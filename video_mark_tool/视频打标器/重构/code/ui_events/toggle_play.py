# This is a method from class VideoTagger


def toggle_play(self):
    self.playing = not self.playing
    if self.playing:
        self.play_video()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['toggle_play']
