import tkinter as tk
from video_tagger import VideoTagger

def main():
    root = tk.Tk()
    app = VideoTagger(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()