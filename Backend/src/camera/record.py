import cv2
import os
import time
from datetime import datetime
from pathlib import Path


class ContinuousRecorder:
    def __init__(
        self,
        camera_id=0,
        output_dir=os.environ.get('EV_RECORD_DIR', 'data/raw_buffer'),
        frame_width=1280,
        frame_height=720,
        fps=20,
        segment_duration=180  # 3 minutes per file
    ):
        self.camera_id = camera_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.fps = fps
        self.segment_duration = segment_duration
        
        self.cap = None
        self.writer = None
        self.current_filename = None
        self.segment_start_time = None
        
    def initialize_camera(self):
        """Initialize camera capture."""
        self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {self.camera_id}")
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        # Verify settings
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        print(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps} FPS")
        
    def create_new_segment(self):
        """Create a new video segment file."""
        if self.writer is not None:
            self.writer.release()
            print(f"Completed: {self.current_filename}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_filename = f"cam_{self.camera_id}_{timestamp}.mp4"
        filepath = self.output_dir / self.current_filename
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(
            str(filepath),
            fourcc,
            self.fps,
            (self.frame_width, self.frame_height)
        )
        
        self.segment_start_time = time.time()
        print(f"Started recording: {self.current_filename}")
        
    def should_create_new_segment(self):
        """Check if current segment duration exceeded."""
        if self.segment_start_time is None:
            return True
        
        elapsed = time.time() - self.segment_start_time
        return elapsed >= self.segment_duration
    
    def record(self):
        """Main recording loop - records continuously."""
        try:
            self.initialize_camera()
            
            print(f"Continuous recording started (segments: {self.segment_duration}s)")
            print("Press 'q' to stop")
            
            frame_count = 0
            
            while True:
                ret, frame = self.cap.read()
                
                if not ret:
                    print("Failed to read frame, reconnecting...")
                    time.sleep(1)
                    self.cap.release()
                    self.initialize_camera()
                    continue
                
                # Create new segment if needed
                if self.should_create_new_segment():
                    self.create_new_segment()
                
                # Write frame
                if self.writer is not None:
                    self.writer.write(frame)
                    frame_count += 1
                
                # Display (optional - remove for headless)
                cv2.imshow('Recording', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\nStopping recording...")
                    break
                    
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Release resources."""
        if self.writer is not None:
            self.writer.release()
            print(f"Final segment saved: {self.current_filename}")
        
        if self.cap is not None:
            self.cap.release()
        
        cv2.destroyAllWindows()
        print("Recording stopped")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Continuous video recorder')
    parser.add_argument('--camera', type=int, default=0, help='Camera ID')
    parser.add_argument('--output', default=os.environ.get('EV_RECORD_DIR', 'data/raw_buffer'), help='Output directory')
    parser.add_argument('--width', type=int, default=1280, help='Frame width')
    parser.add_argument('--height', type=int, default=720, help='Frame height')
    parser.add_argument('--fps', type=int, default=20, help='Frames per second')
    parser.add_argument('--segment', type=int, default=180, help='Segment duration (seconds)')
    
    args = parser.parse_args()
    
    recorder = ContinuousRecorder(
        camera_id=args.camera,
        output_dir=args.output,
        frame_width=args.width,
        frame_height=args.height,
        fps=args.fps,
        segment_duration=args.segment
    )
    
    recorder.record()


if __name__ == '__main__':
    main()