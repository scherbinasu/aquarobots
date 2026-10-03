import lgpio
import time
import sys

# --- Настройки ---
PWM_FREQ = 50                 # 50 Гц
PERIOD_NS = int(1e9 / PWM_FREQ)  # 20 000 000 нс (20 мс)
PWM_CHANNEL_1 = 0    # соответствует GPIO 12
PWM_CHANNEL_2 = 1    # соответствует GPIO 13
PWM_FREQ = 50
PWM_CHIP = 0


# Длительности импульсов в наносекундах
PULSE_MIN_NS = 1_000_000      # 1 мс   -> назад
PULSE_STOP_NS = 1_500_000     # 1.5 мс -> стоп
PULSE_MAX_NS = 2_000_000      # 2 мс   -> вперёд

# Отображение логического канала на номер GPIO (BCM)
# По умолчанию: канал 0 = GPIO12, канал 1 = GPIO13
CHANNEL_TO_GPIO = {
    0: 12,
    1: 13,
}

class HardMotor:
    """Управление мотором (ESC) через аппаратный ШИМ на lgpio."""
    reversed = False
    cor_kf = 1          # коэффициент умножения скорости
    just_kf = 1.35      # пропорция вперёд/назад (для компенсации разницы)

    def __init__(self, pwm_channel, hz=PWM_FREQ, chip=0):
        """
        pwm_channel: 0 (GPIO12) или 1 (GPIO13)
        hz: частота (по умолч. 50)
        chip: номер gpiochip (обычно 0)
        """
        self.pwm_channel = pwm_channel
        self.gpio_pin = CHANNEL_TO_GPIO.get(pwm_channel)
        if self.gpio_pin is None:
            raise ValueError(f"Неверный канал: {pwm_channel}. Допустимо 0 или 1.")
        self.freq = hz
        self.chip = chip
        self.handle = None
        self._is_setup = False
        self._init_pwm()

    def _init_pwm(self):
        """Открыть gpiochip и захватить пин как выход для ШИМ."""
        try:
            self.handle = lgpio.gpiochip_open(self.chip)
            # Освободить пин, если он уже был занят (игнорируем ошибку)
            try:
                lgpio.gpio_free(self.handle, self.gpio_pin)
            except lgpio.error:
                pass
            lgpio.gpio_claim_output(self.handle, self.gpio_pin)
            self._is_setup = True
        except Exception as e:
            raise RuntimeError(f"Не удалось инициализировать GPIO {self.gpio_pin}: {e}")

    def start(self):
        """Установить мотор в нейтраль (стоп)."""
        self.set_motor(0)

    def set_motor(self, power_percent, output=False):
        """
        power_percent: от -100 до 100.
        output: если True, печатать отладочную информацию.
        """
        if not self._is_setup:
            self._init_pwm()

        # Ограничение и учёт реверса
        p = max(-100, min(100, (power_percent * self.cor_kf) * ((2 * int(self.reversed)) - 1)))

        # Преобразование в длительность импульса (нс)
        if p >= 0:
            pulse_ns = PULSE_STOP_NS + (p / (100.0 * self.just_kf)) * (PULSE_MAX_NS - PULSE_STOP_NS)
        else:
            pulse_ns = PULSE_STOP_NS + (p / 100.0) * (PULSE_STOP_NS - PULSE_MIN_NS)

        pulse_ns = max(PULSE_MIN_NS, min(PULSE_MAX_NS, pulse_ns))

        # Преобразовать в процент заполнения (0..100) относительно периода
        duty_percent = (pulse_ns / PERIOD_NS) * 100.0

        # Отправить ШИМ-сигнал
        lgpio.tx_pwm(self.handle, self.gpio_pin, self.freq, duty_percent, 0, 0)

        if output:
            print(f"Канал {self.pwm_channel} (GPIO{self.gpio_pin}): {p:4}% -> импульс {pulse_ns/1e6:.2f} мс (duty {duty_percent:.2f}%)")

    def stop(self):
        """Остановить ШИМ и освободить ресурсы."""
        if self._is_setup and self.handle is not None:
            try:
                lgpio.tx_pwm(self.handle, self.gpio_pin, 0, 0, 0, 0)
                lgpio.gpio_free(self.handle, self.gpio_pin)
                lgpio.gpiochip_close(self.handle)
            except:
                pass
            self._is_setup = False
            self.handle = None

    def __del__(self):
        self.stop()
