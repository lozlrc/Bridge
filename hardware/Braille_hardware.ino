#include <Arduino.h>

#define NUM_MOTORS 4

const int motorPins[NUM_MOTORS][4] = {
  {13, 12, 14, 27},
  {26, 25, 33, 32},
  {23, 22, 21, 19},
  {18, 5, 4, 2}
};

const int stepDelay = 2;
const int STEPS_PER_REV = 4096;
const int HALF_REV_STEPS = STEPS_PER_REV / 2;
const unsigned long DISPLAY_HOLD_MS = 5000;
const float BLANK_ANGLE = 239.75;
const float STARTUP_REFERENCE_ANGLE = BLANK_ANGLE;

long currentSteps[NUM_MOTORS];
int currentPhase[NUM_MOTORS] = {0, 0, 0, 0};

int stepSequence[8][4] = {
  {1, 0, 0, 0},
  {1, 1, 0, 0},
  {0, 1, 0, 0},
  {0, 1, 1, 0},
  {0, 0, 1, 0},
  {0, 0, 1, 1},
  {0, 0, 0, 1},
  {1, 0, 0, 1}
};

void setMotorStep(int motor, int a, int b, int c, int d) {
  digitalWrite(motorPins[motor][0], a);
  digitalWrite(motorPins[motor][1], b);
  digitalWrite(motorPins[motor][2], c);
  digitalWrite(motorPins[motor][3], d);
}

void motorOff(int motor) {
  setMotorStep(motor, 0, 0, 0, 0);
}

void allMotorsOff() {
  for (int m = 0; m < NUM_MOTORS; m++) {
    motorOff(m);
  }
}

long angleToSteps(float angle) {
  return round((angle / 360.0) * STEPS_PER_REV);
}

long normalizeSteps(long steps) {
  steps %= STEPS_PER_REV;
  if (steps < 0) {
    steps += STEPS_PER_REV;
  }
  return steps;
}

long shortestStepDiff(long current, long target) {
  long diff = target - current;
  if (diff > HALF_REV_STEPS) {
    diff -= STEPS_PER_REV;
  } else if (diff < -HALF_REV_STEPS) {
    diff += STEPS_PER_REV;
  }
  return diff;
}

void stepMotor(int motor, int direction) {
  currentPhase[motor] = (currentPhase[motor] + direction + 8) % 8;
  setMotorStep(
    motor,
    stepSequence[currentPhase[motor]][0],
    stepSequence[currentPhase[motor]][1],
    stepSequence[currentPhase[motor]][2],
    stepSequence[currentPhase[motor]][3]
  );
  currentSteps[motor] = normalizeSteps(currentSteps[motor] + direction);
}

float charToAngle(char c) {
  c = tolower(c);

  if (c == ' ') return BLANK_ANGLE;
  if (c == 'a') return 98.00;
  if (c == 'b') return 103.50;
  if (c == 'c') return 108.50;
  if (c == 'd') return 114.25;
  if (c == 'e') return 120.25;
  if (c == 'f') return 125.25;
  if (c == 'g') return 131.00;
  if (c == 'h') return 136.50;
  if (c == 'i') return 141.75;
  if (c == 'j') return 147.50;
  if (c == 'k') return 152.50;
  if (c == 'l') return 158.38;
  if (c == 'm') return 164.13;
  if (c == 'n') return 168.88;
  if (c == 'o') return 174.63;
  if (c == 'p') return 180.00;
  if (c == 'q') return 185.38;
  if (c == 'r') return 191.13;
  if (c == 's') return 195.88;
  if (c == 't') return 201.63;
  if (c == 'u') return 207.50;
  if (c == 'v') return 212.50;
  if (c == 'w') return 218.25;
  if (c == 'x') return 223.50;
  if (c == 'y') return 229.00;
  if (c == 'z') return 234.75;
  if (c == '!') return 245.25;
  if (c == '\'') return 250.75;
  if (c == ',') return 256.25;
  if (c == '-') return 261.75;
  if (c == '.') return 267.25;
  if (c == '?') return 272.75;
  if (c == '^') return 278.25;
  if (c == '#') return 283.75;
  if (c == '0') return 289.25;
  if (c == '1') return 294.75;
  if (c == '2') return 300.25;
  if (c == '3') return 305.75;
  if (c == '4') return 311.25;
  if (c == '5') return 316.75;
  if (c == '6') return 322.25;
  if (c == '7') return 327.75;
  if (c == '8') return 333.25;
  if (c == '9') return 338.75;

  return BLANK_ANGLE;
}

void goToAnglesTogether(float targetAngles[]) {
  long targetSteps[NUM_MOTORS];
  long diffSteps[NUM_MOTORS];
  int directions[NUM_MOTORS];
  long remaining[NUM_MOTORS];
  bool motorsStillMoving = true;

  for (int m = 0; m < NUM_MOTORS; m++) {
    targetSteps[m] = normalizeSteps(angleToSteps(targetAngles[m]));
    currentSteps[m] = normalizeSteps(currentSteps[m]);
    diffSteps[m] = shortestStepDiff(currentSteps[m], targetSteps[m]);
    directions[m] = diffSteps[m] >= 0 ? 1 : -1;
    remaining[m] = abs(diffSteps[m]);
  }

  while (motorsStillMoving) {
    motorsStillMoving = false;
    for (int m = 0; m < NUM_MOTORS; m++) {
      if (remaining[m] > 0) {
        stepMotor(m, directions[m]);
        remaining[m]--;
        motorsStillMoving = true;
      }
    }

    if (motorsStillMoving) {
      delay(stepDelay);
    }
  }

  for (int m = 0; m < NUM_MOTORS; m++) {
    currentSteps[m] = normalizeSteps(targetSteps[m]);
  }
}

void displayWord4(char c1, char c2, char c3, char c4) {
  float targets[NUM_MOTORS] = {
    charToAngle(c1),
    charToAngle(c2),
    charToAngle(c3),
    charToAngle(c4)
  };

  goToAnglesTogether(targets);
}

void displayChunk(String chunk) {
  chunk.toLowerCase();
  chunk.replace("\r", "");

  while (chunk.length() < 4) chunk += ' ';
  if (chunk.length() > 4) chunk = chunk.substring(0, 4);

  displayWord4(chunk[0], chunk[1], chunk[2], chunk[3]);
}

void setup() {
  for (int m = 0; m < NUM_MOTORS; m++) {
    for (int p = 0; p < 4; p++) {
      pinMode(motorPins[m][p], OUTPUT);
    }
    currentSteps[m] = angleToSteps(STARTUP_REFERENCE_ANGLE);
    currentPhase[m] = 0;
    motorOff(m);
  }

  Serial.begin(115200);
  Serial.setTimeout(50);
}

void loop() {
  if (Serial.available() > 0) {
    String chunk = Serial.readStringUntil('\n');
    if (chunk.length() > 0) {
      displayChunk(chunk);
      delay(DISPLAY_HOLD_MS);
      allMotorsOff();
    }
  }
}
