package clio.core;

import com.cronutils.descriptor.CronDescriptor;
import com.cronutils.model.CronType;
import com.cronutils.model.definition.CronDefinitionBuilder;
import com.cronutils.model.time.ExecutionTime;
import com.cronutils.parser.CronParser;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.util.Locale;

public class Cron {

    public static Cron of(String schedule) {
        if (schedule.contains(" @")) {
            var ss = schedule.split(" @");
            return new Cron(ss[0], ss[1]);
        }
        return new Cron(schedule, null);
    }

    public static Cron of(String schedule, String tz)
    {
        return new Cron(schedule, tz);
    }

    private static final CronParser parser = new CronParser(CronDefinitionBuilder.instanceDefinitionFor(CronType.UNIX));
    private static final CronDescriptor descriptor = CronDescriptor.instance(Locale.UK);

    private final String desc;
    private final ExecutionTime execTime;
    private final ZoneId tz;

    public Cron(String schedule, String tz) {
        var cron = parser.parse(schedule);
        this.execTime = ExecutionTime.forCron(cron);
        if (tz == null)
            tz = "UTC";
        this.desc = descriptor.describe(cron) + " " + tz;
        this.tz = "UTC".equals(tz) ? null : ZoneId.of(tz);
    }

    public LocalDateTime next(LocalDateTime now) {
        var zonedNow = ZonedDateTime.of(now, ZoneOffset.UTC);
        if (this.tz != null)
            zonedNow = zonedNow.toInstant().atZone(this.tz);
        var zonedNext = this.execTime.nextExecution(zonedNow).get();
        if (this.tz != null)
            zonedNext = zonedNext.toInstant().atZone(ZoneOffset.UTC);
        return LocalDateTime.ofInstant(zonedNext.toInstant(), ZoneOffset.UTC);
    }

    public LocalDateTime prev(LocalDateTime now) {
        var zonedNow = ZonedDateTime.of(now, ZoneOffset.UTC);
        if (this.tz != null)
            zonedNow = zonedNow.toInstant().atZone(this.tz);
        var zonedPrev = this.execTime.lastExecution(zonedNow).get();
        if (this.tz != null)
            zonedPrev = zonedPrev.toInstant().atZone(ZoneOffset.UTC);
        return LocalDateTime.ofInstant(zonedPrev.toInstant(), ZoneOffset.UTC);
    }

    public String desc() {
        return this.desc;
    }
}
