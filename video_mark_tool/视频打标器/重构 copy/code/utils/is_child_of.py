# This is a method from class VideoTagger

def is_child_of(self, child, parent):
    """检查一个控件是否是另一个控件的子控件"""
    while child is not None:
        if child == parent:
            return True
        try:
            child = child.master
        except:
            break
    return False

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['is_child_of']
