class PIDController:
    def __init__(self,
                 kp: float,
                 ki: float,
                 kd: float,
                 dt: float,
                 output_limits: tuple[float, float] = None
                ):
        """
        PID Controller Initialization

        :param kp: Proportional gain
        :param ki: Integral gain
        :param kd: Derivative gain
        :param dt: Control loop interval (seconds)
        :param output_limits: Output constraint range (min, max) for anti-windup protection
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = dt  # Control interval
        
        # State variables
        self.integral_err = 0.0  # Accumulated integral error
        self.prev_err = 0.0      # Previous error (for derivative calculation)
        self.output_limits = output_limits  # Output constraints
        
    def update(self, err: float) -> float:
        """
        Calculate PID control output
        
        :param err: Current error (setpoint - process variable)
        :return: Control output
        """
        # 1. Proportional term calculation
        proportional = self.kp * err
        
        # 2. Integral term calculation (with anti-windup logic)
        # Calculate unrestricted integral first
        self.integral_err += err * self.dt
        integral = self.ki * self.integral_err
        
        # 3. Derivative term calculation (noise reduction using current and previous error)
        # Prevent division by zero (dt should be > 0 in practical applications)
        derivative = self.kd * (err - self.prev_err) / self.dt if self.dt > 0 else 0.0
        
        # 4. Total output calculation
        output = proportional + integral + derivative
        
        # 5. Output limiting and integral separation (anti-windup)
        if self.output_limits is not None:
            output_min, output_max = self.output_limits
            # Constrain output within limits
            output = max(min(output, output_max), output_min)
            
            # Integral separation: stop integral accumulation when output is saturated
            if (output == output_max and err > 0) or (output == output_min and err < 0):
                self.integral_err -= err * self.dt  # Rollback current integration
        
        # Update previous error for next calculation
        self.prev_err = err
        
        return output
    
    def reset(self):
        """Reset PID controller state (for restarting control process)"""
        self.integral_err = 0.0
        self.prev_err = 0.0