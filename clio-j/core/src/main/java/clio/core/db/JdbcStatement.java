package clio.core.db;

import java.sql.Date;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.time.LocalDate;
import java.time.LocalDateTime;

public class JdbcStatement {

    protected final PreparedStatement stmt;
    protected final Syntax syntax;

    private int i = 0;

    public JdbcStatement(PreparedStatement stmt, Syntax syntax) {
        this.stmt = stmt;
        this.syntax = syntax;
    }

    public void setDttm(LocalDateTime dttm) throws SQLException {
        stmt.setTimestamp(++i, syntax.toTimestamp(dttm));
    }

    public void setDt(LocalDate date) throws SQLException {
        stmt.setDate(++i, Date.valueOf(date));
    }

    public void setString(String str) throws SQLException {
        stmt.setString(++i, str);
    }

    public void setBool(boolean bool) throws SQLException {
        stmt.setBoolean(++i, bool);
    }

    public void setInt(int in) throws SQLException {
        stmt.setInt(++i, in);
    }

    public void setLong(long lng) throws SQLException {
        stmt.setLong(++i, lng);
    }

    public void setFloat(float flt) throws SQLException {
        stmt.setFloat(++i, flt);
    }

    public void setDouble(double dbl) throws SQLException {
        stmt.setDouble(++i, dbl);
    }
}
