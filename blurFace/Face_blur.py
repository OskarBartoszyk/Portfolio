import cv2

# Załadowanie Haar Cascade
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
if face_cascade.empty():
    print("Error: Could not load Haar cascade file.")
    exit()

# Odpalenie kamerki
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

while True:
    # Przechwyć frame po framie
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to capture frame.")
        break
    
    # Konwertuj na odcienie szarości
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Wykrywanie twarzy
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4)
    
    # Blur dla każdej wykrytej twarzy
    for (x, y, w, h) in faces:
        face_region = frame[y:y+h, x:x+w]  # Wybierz region twarzy
        blurred_face = cv2.GaussianBlur(face_region, (51, 51), 30)  # Gaussian blur
        frame[y:y+h, x:x+w] = blurred_face  # Podmień na zblurrowaną twarz

    cv2.imshow('Face Detection with Blur', frame)
    
    # 'q' przerywa działanie programu
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
