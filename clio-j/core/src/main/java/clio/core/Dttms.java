package clio.core;

import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.regex.Pattern;

import static clio.core.Strings.f;


public class Dttms {

    private static final DateTimeFormatter fmt_dt = DateTimeFormatter.ofPattern("yyyyMMdd");
    private static final DateTimeFormatter fmt_dt_sql = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    private static final DateTimeFormatter fmt_hours = DateTimeFormatter.ofPattern("yyyyMMdd_HH");
    private static final DateTimeFormatter fmt_minutes = DateTimeFormatter.ofPattern("yyyyMMdd_HHmm");
    private static final DateTimeFormatter fmt_seconds = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss");
    private static final DateTimeFormatter fmt_millis = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmssSSS");
    private static final DateTimeFormatter fmt_micros = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmssSSSSSS");
    private static final DateTimeFormatter fmt_nanos = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmssSSSSSSSSS");

    private static final DateTimeFormatter fmt_sql = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSSSSSSSS");
    private static final DateTimeFormatter fmt_kdb = DateTimeFormatter.ofPattern("yyyy.MM.dd'D'HH:mm:ss.SSSSSSSSS");

    private static final DateTimeFormatter fmt_iso8601 = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss'Z'");

    private static final Pattern durationPattern = Pattern.compile("(\\d+)([a-zA-Z])");

    public static final LocalTime EOD = LocalTime.of(22, 0);

    public static LocalDateTime minutely(LocalDateTime dttm) {
        return LocalDateTime.of(dttm.getYear(), dttm.getMonth(), dttm.getDayOfMonth(), dttm.getHour(), dttm.getMinute());
    }

    public static LocalDateTime now(LocalDateTime now) {
        return now != null ? now : LocalDateTime.now();
    }

    public static LocalDateTime parseDttm(String dttm) {
        return parseDttm(dttm, null);
    }

    public static LocalDateTime parseDttm(String dttm, LocalDateTime now) {

        if (dttm.contains("@")) {
            var split = dttm.split("@");
            if (split.length == 2) {
                var dttmLocal = parseDttm(split[0], now);
                return convertTz(dttmLocal, split[1], "UTC");
            }
        }

        var split = dttm.split("-");
        if (split.length == 2)
            return parseDttm(split[0], now).minus(parseDuration(split[1]));

        split = dttm.split("\\+");
        if (split.length == 2)
            return parseDttm(split[0], now).plus(parseDuration(split[1]));

        return switch (dttm.toLowerCase()) {
            case "now" -> now(now);
            case "eod" -> eod(now);
            case "sod" -> sod(now);
            case "today", "t" -> now(now).toLocalDate().atStartOfDay();
            case "yesterday", "yd" -> now(now).toLocalDate().minusDays(1).atStartOfDay();
            default -> switch (dttm.length()) {
                case 11 -> LocalDateTime.parse(dttm, fmt_hours);
                case 13 -> LocalDateTime.parse(dttm, fmt_minutes);
                case 15 -> LocalDateTime.parse(dttm, fmt_seconds);
                case 18 -> LocalDateTime.parse(dttm, fmt_millis);
                case 21 -> LocalDateTime.parse(dttm, fmt_micros);
                case 24 -> LocalDateTime.parse(dttm, fmt_nanos);
                default -> throw new RuntimeException("Unable to parse dttm [" + dttm + "]");
            };
        };

    }

    public static LocalDateTime parseOptionalDttm(String dttm) {
        return Strings.hasValue(dttm) ? parseDttm(dttm) : null;
    }

    public static LocalDate parseDt(String dt) {
        if (dt.contains("-"))
            return parseDtSql(dt);
        return LocalDate.parse(dt, fmt_dt);
    }

    public static LocalDate parseOptionalDt(String dt) {
        return Strings.hasValue(dt) ? parseDt(dt) : null;
    }

    public static LocalDate parseDtSql(String dt) {
        return LocalDate.parse(dt, fmt_dt_sql);
    }

    public static LocalTime parseTime(String str) {
        return parseTime(str, false);
    }

    public static LocalTime parseTime(String str, boolean canBeJustHours) {
        var split = str.split(":");
        if (split.length == 1 && canBeJustHours) {
            return LocalTime.of(Integer.parseInt(split[0]), 0);
        }

        if (split.length == 2 || split.length == 3) {
            var hours = Integer.parseInt(split[0]);
            var minutes = Integer.parseInt(split[1]);
            if (split.length == 2)
                return LocalTime.of(hours, minutes);

            var seconds = Integer.parseInt(split[2]);
            return LocalTime.of(hours, minutes, seconds);
        }

        throw new RuntimeException("Unknown time [" + str + "]");
    }

    public static Duration parseDuration(String str) {
        try {
            var strLower = str.toLowerCase();
            if (strLower.endsWith("am"))
                return Duration.between(LocalTime.MIDNIGHT, parseTime(str.substring(0, strLower.length() - 2), true));

            if (strLower.endsWith("pm")) {
                var duration = Duration.between(LocalTime.MIDNIGHT, parseTime(str.substring(0, strLower.length() - 2), true));
                var h12 = Duration.ofHours(12);
                if (duration.compareTo(h12) > 0)
                    throw new RuntimeException(str + " is not valid pm time");
                return h12.plus(duration);
            }

            var m = durationPattern.matcher(str);
            if (m.matches()) {
                var num = Integer.parseInt(m.group(1));
                var period = m.group(2);
                return switch (period) {
                    case "s" -> Duration.ofSeconds(num);
                    case "m" -> Duration.ofMinutes(num);
                    case "h" -> Duration.ofHours(num);
                    case "d", "D" -> Duration.ofDays(num);
                    default -> throw new RuntimeException("Unknown duration [" + period + "]");
                };
            }

            return Duration.between(LocalTime.MIDNIGHT, parseTime(str));

        } catch (Exception ex) {
            throw new RuntimeException("Unable to parse duration [" + str + "]");
        }
    }

    public static Period parsePeriod(String str) {
        try {
            var m = durationPattern.matcher(str);
            if (m.matches()) {
                var num = Integer.parseInt(m.group(1));
                var period = m.group(2);
                return switch (period) {
                    case "d", "D" -> Period.ofDays(num);
                    case "W" -> Period.ofWeeks(num);
                    case "M" -> Period.ofMonths(num);
                    case "Y" -> Period.ofYears(num);

                    default -> throw new RuntimeException("Unknown period [" + period + "]");
                };
            }
            throw new RuntimeException("no match");
        } catch (Exception ex) {
            throw new RuntimeException("Unable to parse period [" + str + "]");
        }
    }

    public static int comparePeriods(String p1, String p2) {
        var m1 = durationPattern.matcher(p1);
        if (!m1.matches())
            throw new RuntimeException("Invalid Period [" + p1 + "]");
        var n1 = Integer.parseInt(m1.group(1));
        var t1 = m1.group(2);

        var m2 = durationPattern.matcher(p2);
        if (!m2.matches())
            throw new RuntimeException("Invalid Period [" + p2 + "]");
        var n2 = Integer.parseInt(m2.group(1));
        var t2 = m2.group(2);

        if (!t1.equals(t2))
            throw new RuntimeException(f("Incompatible types [{}!={}]", t1, t2));

        return Integer.compare(n1, n2);
    }

    public static String formatDttm(LocalDateTime dttm) {
        int nanos = dttm.getNano();
        int micros = (nanos / 1_000) % 1_000;
        int millis = nanos / 1_000_000;
        nanos = nanos % 1_000;

        if (nanos != 0)
            return dttm.format(fmt_nanos);
        if (micros != 0)
            return dttm.format(fmt_micros);
        if (millis != 0)
            return dttm.format(fmt_millis);
        if (dttm.getSecond() != 0)
            return dttm.format(fmt_seconds);
        if (dttm.getMinute() != 0)
            return dttm.format(fmt_minutes);
        return dttm.format(fmt_hours);
    }

    public static String formatDt(LocalDate date) {
        return date.format(fmt_dt);
    }

    public static String formatDttmMinutes(LocalDateTime dttm) {
        return dttm.format(fmt_minutes);
    }

    public static String formatSql(LocalDateTime dttm) {
        return dttm.format(fmt_sql);
    }

    public static String formatKdb(LocalDateTime dttm) {
        return dttm.format(fmt_kdb);
    }

    public static String formatSql(LocalDate date) {
        return date.format(fmt_dt_sql);
    }

    public static String formatISO(LocalDateTime dttm) {
        return dttm.format(fmt_iso8601);
    }

    public static long toEpochNanos(LocalDateTime dttm) {
        var instant = dttm.toInstant(ZoneOffset.UTC);
        return instant.getEpochSecond() * 1_000_000_000L + instant.getNano();
    }

    public static LocalDate fromYYYYMMDD(long yyyymmdd) {
        var str = String.valueOf(yyyymmdd);
        return LocalDate.parse(str, fmt_dt);
    }

    public static LocalDateTime fromEpochNanos(long epochNanos) {
        var nanos = epochNanos % 1_000_000_000L;
        var seconds = (epochNanos - nanos) / 1_000_000_000L;
        return LocalDateTime.ofEpochSecond(seconds, (int)nanos, ZoneOffset.UTC);
    }

    public static LocalDateTime fromEpochMicros(long epochMicros) {
        var micros = epochMicros % 1_000_000L;
        var seconds = (epochMicros - micros) / 1_000_000L;
        return LocalDateTime.ofEpochSecond(seconds, (int)(micros * 1_000), ZoneOffset.UTC);
    }

    public static LocalDateTime fromEpochMillis(long epochMillis) {
        var millis = epochMillis % 1_000L;
        var seconds = (epochMillis - millis) / 1_000L;
        return LocalDateTime.ofEpochSecond(seconds, (int)(millis * 1_000_000), ZoneOffset.UTC);
    }

    public static LocalDateTime fromEpochInferred(long epochUnknown) {
        if (epochUnknown > 1000000000000000000L)
            return fromEpochNanos(epochUnknown);
        if (epochUnknown > 1000000000000000L)
            return fromEpochMicros(epochUnknown);
        if (epochUnknown > 1000000000000L)
            return fromEpochMillis(epochUnknown);
        return LocalDateTime.ofEpochSecond(epochUnknown, 0, ZoneOffset.UTC);
    }

    public static LocalDateTime eod(LocalDateTime dttm) {
        return eod(dttm, 0);
    }

    public static LocalDateTime eod(LocalDateTime dttm, int offsetDays) {
        var dt = dttm.toLocalDate();
        if (dttm.toLocalTime().isAfter(EOD))
            dt = dt.plusDays(1);
        if (offsetDays != 0)
            dt = dt.plusDays(offsetDays);
        return LocalDateTime.of(dt, EOD);
    }

    public static LocalDateTime sod(LocalDateTime dttm) {
        return sod(dttm, 0);
    }

    public static LocalDateTime sod(LocalDateTime dttm, int offsetDays) {
        var dt = dttm.toLocalDate();
        if (!dttm.toLocalTime().isAfter(EOD))
            dt = dt.minusDays(1);
        if (offsetDays != 0)
            dt = dt.plusDays(offsetDays);
        return LocalDateTime.of(dt, EOD);
    }

    public static boolean isWeekend(LocalDate dt) {
        var dow = dt.getDayOfWeek();
        return dow == DayOfWeek.SATURDAY || dow == DayOfWeek.SUNDAY;
    }

    public static LocalDate minusBusDays(LocalDate dt, int days) {
        if (days < 0)
            return plusBusDays(dt, -days);

        while (days != 0) {
            dt = dt.minusDays(1);
            if (!isWeekend(dt))
                days -= 1;
        }
        return dt;
    }

    public static LocalDate plusBusDays(LocalDate dt, int days) {
        if (days < 0)
            return minusBusDays(dt, -days);

        while (days != 0) {
            dt = dt.plusDays(1);
            if (!isWeekend(dt))
                days -= 1;
        }
        return dt;
    }

    public static LocalDate tradeDt() {
        return tradeDt(null);
    }

    public static LocalDate tradeDt(LocalDateTime now) {
        now = now(now);
        var tradeDt = now.toLocalDate();
        if (now.toLocalTime().isAfter(EOD))
            tradeDt = tradeDt.plusDays(1);

        while (isWeekend(tradeDt))
            tradeDt = tradeDt.plusDays(1);

        return tradeDt;
    }

    public static LocalDateTime parseOffsetDttm(String dttm) {
        var offsetDttm = OffsetDateTime.parse(dttm);
        return offsetDttm.toZonedDateTime().withZoneSameInstant(ZoneOffset.UTC).toLocalDateTime();
    }

    public static LocalDateTime epocToNull(LocalDateTime dttm) {
        if ((dttm != null) && (dttm.toInstant(ZoneOffset.UTC).getEpochSecond() == 0))
            return null;
        return dttm;
    }

    public static LocalDateTime convertTz(LocalDateTime dttm, String fromTz, String toTz) {
        return ZonedDateTime.of(dttm, ZoneId.of(fromTz)).withZoneSameInstant(ZoneId.of(toTz)).toLocalDateTime();
    }
}
