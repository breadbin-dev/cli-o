package clio.core.db;

import clio.core.Dttms;

import java.sql.Date;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneOffset;

import static clio.core.Strings.f;

public interface Syntax {

    default JdbcStatement statement(PreparedStatement stmt) {
        return new JdbcStatement(stmt, this);
    }

    default JdbcResult result(ResultSet result) {
        return new JdbcResult(result, this);
    }

    default String typeForField(Class<?> cls) {
        if (cls == String.class || cls.isEnum())
            return "String";
        if (cls == Double.class || cls == double.class)
            return "Float64";
        if (cls == Integer.class || cls == int.class || cls == Long.class || cls == long.class)
            return "Int64";
        if (cls == Boolean.class || cls == boolean.class)
            return "Boolean";

        throw new RuntimeException(f("Unsupported type {}", cls.getSimpleName()));
    }

    default String columnForField(String name, Class<?> cls, boolean nullable) {
        var t = typeForField(cls);
        if (nullable)
            t = "Nullable(" + t + ")";
        return f("    {} {}", name, t);
    }

    default String formatDttm(LocalDateTime dttm) {
        return "'" + Dttms.formatSql(dttm) + "'";
    }

    default Date toDate(LocalDate dt) {
        return dt == null ? null : Date.valueOf(dt);
    }

    default LocalDate fromDate(Date dt) {
        return dt == null ? null : dt.toLocalDate();
    }

    default Timestamp toTimestamp(LocalDateTime dttm) {
        return dttm == null ? null : Timestamp.from(dttm.toInstant(ZoneOffset.UTC));
    }

    default LocalDateTime fromTimestamp(Timestamp ts) {
        return fromTimestamp(ts, true);
    }

    default LocalDateTime fromTimestamp(Timestamp ts, boolean epocToNull) {
        if (ts == null)
            return null;

        var dttm = ts.toLocalDateTime();
        return epocToNull ? Dttms.epocToNull(dttm) : dttm;
    }
}
