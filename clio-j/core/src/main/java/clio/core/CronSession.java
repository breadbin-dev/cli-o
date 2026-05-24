package clio.core;

import java.time.LocalDateTime;

public record CronSession(Cron start, Cron end) {

    public static CronSession of(String startSchedule, String endSchedule) {
        return new CronSession(Cron.of(startSchedule), Cron.of(endSchedule));
    }

    public boolean isOpen(LocalDateTime dttm) {
        var prevStart = start.prev(dttm);
        var prevOpen = end.prev(dttm);
        return prevStart.isAfter(prevOpen);
    }

    public boolean isClosed(LocalDateTime dttm) {
        return !isOpen(dttm);
    }
}
