package clio.core.db;

import clio.core.Strings;

import java.sql.Connection;
import java.sql.SQLException;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;

public class Database {

    private final Map<Class<?>, JdbcAdapter<?>> adapters = new HashMap<>();

    private final Connection conn;

    public Database(Connection conn, JdbcAdapter<?>... adapters) {
        this.conn = conn;

        this.adapters.put(LocalDate.class, new LocalDateAdapter());
        for (var adapter : adapters)
            this.adapters.put(adapter.adapterCls(), adapter);
    }

    public <T> void write(T obj) {
        var adapter = this.<T>getAdapter(obj.getClass());

        var sql = new StringBuilder();
        sql.append("insert into ");
        sql.append(adapter.table());
        sql.append(" values (");
        sql.append(adapter.placeHolder());
        sql.append(")");

        try (var statement = conn.prepareStatement(sql.toString())){
            adapter.insert(obj, statement);
            statement.executeUpdate();
        }
        catch (SQLException ex) {
            throw new RuntimeException(ex);
        }
    }

    public <T> void writeAll(Collection<T> objs) {
        for (var obj : objs)
            this.write(obj);
    }

    protected <T> JdbcAdapter<T> getAdapter(Class<?> adapterType) {
        var adapter = this.adapters.get(adapterType);
        if (adapter == null)
            throw new RuntimeException("No adapter registered for " + adapterType);
        return (JdbcAdapter<T>)adapter;
    }

    public <T> List<T> select(String query, Class<T> cls, LocalDateTime fromDttm, LocalDateTime toDttm) {
        return select(query, cls, fromDttm, toDttm, null);
    }

    public <T> List<T> selectAsOf(String query, Class<T> cls, LocalDateTime asOfDttm, String suffix) {
        query += query.contains(" where ") ? " and " : " where ";
        query += "asserted_from <= " + Databases.filterDttm(asOfDttm) + " and (asserted_to is null or asserted_to > " + Databases.filterDttm(asOfDttm) + ")";
        return select(query, cls, null, null, suffix);
    }

    public <T> List<T> select(String query, Class<T> cls, LocalDateTime fromDttm, LocalDateTime toDttm, String suffix) {
        var clause = query.contains(" where ") ? " and " : " where ";

        if (fromDttm != null && toDttm != null)
            query += clause + "dttm between " + Databases.filterDttm(fromDttm.plusNanos(1)) + " and " + Databases.filterDttm(toDttm);
        else if (fromDttm != null)
            query += clause + "dttm > " + Databases.filterDttm(fromDttm);
        else if (toDttm != null)
            query += clause + "dttm <= " + Databases.filterDttm(toDttm);

        if (Strings.hasValue(suffix))
            query += " " + suffix;

        return select(query, cls);
    }

    public <T> List<T> select(String query, Class<T> cls) {
        var adapter = this.<T>getAdapter(cls);

        if (query.contains("{table}"))
            query = query.replace("{table}", adapter.table());

        try (var statement = conn.prepareStatement(query)) {
            try (var results = statement.executeQuery()) {
                var selection = new ArrayList<T>();
                while(results.next())
                    selection.add(adapter.select(results));

                return selection;
            }
        } catch (SQLException ex) {
            throw new RuntimeException(ex);
        }
    }
}
