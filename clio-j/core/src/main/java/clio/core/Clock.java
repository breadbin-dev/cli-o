package clio.core;

import java.time.LocalDateTime;
import java.time.temporal.TemporalAmount;
import java.time.temporal.TemporalUnit;

public interface Clock {
    class MockClock implements Clock {

        private LocalDateTime now;

        @Override
        public LocalDateTime now() {
            return now;
        }

        public void set(LocalDateTime now) {
            this.now = now;
        }

        public void tick(TemporalAmount period) {
            now = now.plus(period);
        }

        public void tick(long period, TemporalUnit unit) {
            now = now.plus(period, unit);
        }
    }

    static Clock system() {
        return new SystemClock();
    }

    LocalDateTime now();
}

class SystemClock implements Clock {
    @Override
    public LocalDateTime now() {
        return LocalDateTime.now();
    }
}
