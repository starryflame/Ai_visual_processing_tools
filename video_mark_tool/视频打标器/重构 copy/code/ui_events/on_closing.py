# This is a method from class VideoTagger


def on_closing(self):
    if self.cap:
        self.cap.release()
    self.root.destroy()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['on_closing']
