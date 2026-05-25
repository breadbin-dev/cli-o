package clio.core.db;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.time.LocalDateTime;

public class JdbcResult {

    protected final ResultSet result;
    protected final Syntax syntax;

    private int i = 0;

    public JdbcResult(ResultSet result, Syntax syntax) {
        this.result = result;
        this.syntax = syntax;
    }

    public LocalDateTime getDttm() throws SQLException {
        return syntax.fromTimestamp(result.getTimestamp(++i));
    }

    public LocalDate getDt() throws SQLException {
        return result.getDate(++i).toLocalDate();
    }

    public String getString() throws SQLException {
        return result.getString(++i);
    }

    public boolean getBool() throws SQLException {
        return result.getBoolean(++i);
    }

    public int getInt() throws SQLException {
        return result.getInt(++i);
    }

    public long getLong() throws SQLException {
        return result.getLong(++i);
    }

    public float getFloat() throws SQLException {
        return result.getFloat(++i);
    }

    public double getDouble() throws SQLException {
        return result.getDouble(++i);
    }
}