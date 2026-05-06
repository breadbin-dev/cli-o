package clio.core.db;

import clio.core.Collections;
import clio.core.Dttms;
import clio.core.Strings;

import java.sql.*;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneOffset;

public abstract class JdbcAdapter<T> {

    private final Class<T> adapterCls;
    private final String table;
    private final String placeHolder;

    public JdbcAdapter(Class<T> adapterCls) {
        this(adapterCls, Strings.camelToSnake(adapterCls.getSimpleName()));
    }

    public JdbcAdapter(Class<T> adapterCls, String table) {
        this.adapterCls = adapterCls;
        this.table = table;
        this.placeHolder = String.join(",", Collections.repeat("?", adapterCls.getDeclaredFields().length));
    }

    Class<T> adapterCls() {
        return adapterCls;
    }

    String placeHolder() {
        return placeHolder;
    }

    public String table() {
        return table;
    }

    public abstract void insert(T obj, PreparedStatement stmt) throws SQLException;

    public abstract T select(ResultSet result) throws SQLException;

    public Date toDate(LocalDate dt) {
        return dt == null ? null : Date.valueOf(dt);
    }

    public LocalDate fromDate(Date dt) {
        return dt == null ? null : dt.toLocalDate();
    }

    public Timestamp toTimestamp(LocalDateTime dttm) {
        return dttm == null ? null : Timestamp.from(dttm.toInstant(ZoneOffset.UTC));
    }

    public LocalDateTime fromTimestamp(Timestamp ts) {
        return fromTimestamp(ts, true);
    }

    public LocalDateTime fromTimestamp(Timestamp ts, boolean epocToNull) {
        if (ts == null)
            return null;

        var dttm = ts.toLocalDateTime();
        return epocToNull ? Dttms.epocToNull(dttm) : dttm;
    }
}
