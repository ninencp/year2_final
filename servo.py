import RPi.GPIO as GPIO
import pigpio
import time

servo = 17 #BCM

def cam_move(servo_pin):
    # more info at http://abyz.me.uk/rpi/pigpio/python.html#set_servo_pulsewidth
    pwm = pigpio.pi()
    pwm.set_mode(servo_pin, pigpio.OUTPUT)

    pwm.set_PWM_frequency( servo_pin, 50 )
    pwm.set_servo_pulsewidth( servo_pin, 1500 ) ;

    for deg in range(1500,2501, 100):
        pwm.set_servo_pulsewidth( servo_pin, deg ) ;
        time.sleep(0.75)

    time.sleep(2)
    for deg in range(1500,500, -100):
        pwm.set_servo_pulsewidth( servo_pin, deg ) ;
        time.sleep(0.75)

    for deg in range(500,1501, 1000):
        pwm.set_servo_pulsewidth( servo_pin, deg ) ;
        time.sleep(0.75)

    print( "90 deg" )
    # turning off servo
    print('bye')
    pwm.set_PWM_dutycycle( servo_pin, 0 )
    pwm.set_PWM_frequency( servo_pin, 0 )

