package clio.core.db;

import clio.core.Collections;
import clio.core.Strings;

import java.sql.*;

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

    public abstract void insert(T obj, JdbcStatement stmt) throws SQLException;

    public abstract T select(JdbcResult result) throws SQLException;
}
