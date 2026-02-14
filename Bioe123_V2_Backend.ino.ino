
// CONFIGURATION

#define SENSOR_PIN 2
#define PWM_PIN 9

#define PULSES_PER_ROTATION 2
#define CONTROL_INTERVAL 100   // ms
#define MAX_SAFE_RPM 10000
#define FEEDBACK_DELAY 15000      // 15 seconds

// Feedforward constants (tunable)
float a = 0.02;   // slope
float b = 20;     // offset

float Kp = 0.02;   // Proportional gain (tunable)

// GLOBAL VARIABLES

volatile unsigned long pulseCount = 0;

float rpm = 0;
float targetRPM = 0;

int pwmValue = 0;

bool running = false;
bool feedbackEnabled = false;

unsigned long lastControlTime = 0;
unsigned long startTime = 0;

// SETUP

void setup() {
  Serial.begin(9600);

  pinMode(SENSOR_PIN, INPUT);
  pinMode(PWM_PIN, OUTPUT);

  attachInterrupt(digitalPinToInterrupt(SENSOR_PIN), countPulse, RISING);
}

// MAIN LOOP

void loop() {

  acceptSerial();        // Check for commands from PC

  unsigned long currentTime = millis();

  if (currentTime - lastControlTime >= CONTROL_INTERVAL) {
    calculateRPM();
    runControl();
    applyPWM();
    sendRPM_PWM();

    lastControlTime = currentTime;
  }
}

// INTERRUPT

void countPulse() {
  pulseCount++;
}

// RPM CALCULATION

void calculateRPM() {

  noInterrupts(); // lock (like a mutex)
  unsigned long pulses = pulseCount;
  pulseCount = 0;
  interrupts(); // unlock (like a mutex)

  float rotations = (float)pulses / PULSES_PER_ROTATION;
  float seconds = CONTROL_INTERVAL / 1000.0;

  rpm = (rotations / seconds) * 60.0;

  if (rpm > MAX_SAFE_RPM) { // Safety net incase of malfunction
    running = false;
    pwmValue = 0;
  }
}

// CONTROL LOGIC

void runControl() {

  if (!running) {
    pwmValue = 0;
    feedbackEnabled = false;
    return;
  }

  // Enable feedback after 15 seconds
  if (!feedbackEnabled && millis() - startTime >= FEEDBACK_DELAY) {
    feedbackEnabled = true;
  }

  // Apply proportional correction only after system stabilizes
  if (feedbackEnabled) {
    float error = targetRPM - rpm;
    pwmValue += Kp * error; // ensure speed accuracy, constant PWM alteration until accurate
  }

  // Clamp PWM
  if (pwmValue > 255) pwmValue = 255;
  if (pwmValue < 0) pwmValue = 0;
}

// APPLY PWM TO MOSFET

void applyPWM() {
  analogWrite(PWM_PIN, pwmValue);
}

// SEND DATA THROUGH SERIAL PRINT

void sendRPM_PWM() {
  Serial.print("RPM:");
  Serial.print(rpm);
  Serial.print(",PWM:");
  Serial.println(pwmValue);
}

// ACCEPT SERIAL COMMANDS

void acceptSerial() {

  if (!Serial.available()) return;

  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command.startsWith("SET:")) {
    targetRPM = command.substring(4).toFloat();
  }

  else if (command == "START") {

    running = true;
    feedbackEnabled = false;
    startTime = millis();

    // Initial feedforward PWM estimate
    pwmValue = a * targetRPM + b;

    if (pwmValue > 255) pwmValue = 255;
    if (pwmValue < 0) pwmValue = 0;
  }

  else if (command == "STOP") {
    running = false;
    pwmValue = 0;
    feedbackEnabled = false;
  }
}