package clio.core.db;

import clio.core.Dttms;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.time.LocalDateTime;

public class SQLiteSyntax implements Syntax {
    @Override
    public String typeForField(Class<?> cls) {
        if (cls == LocalDate.class)
            return "String";
        if (cls == LocalDateTime.class)
            return "String";
        return Syntax.super.typeForField(cls);
    }


    @Override
    public JdbcStatement statement(PreparedStatement stmt) {
        return new SQLiteJdbcStatement(stmt, this);
    }

    @Override
    public JdbcResult result(ResultSet result) {
        return new SQLiteJdbcResult(result, this);
    }
}

class SQLiteJdbcResult extends JdbcResult {

    public SQLiteJdbcResult(ResultSet result, Syntax syntax) {
        super(result, syntax);
    }

    @Override
    public LocalDateTime getDttm() throws SQLException {
        return Dttms.parseDttmSql(super.getString());
    }

    @Override
    public LocalDate getDt() throws SQLException {
        return Dttms.parseDtSql(super.getString());
    }
}

class SQLiteJdbcStatement extends JdbcStatement {

    public SQLiteJdbcStatement(PreparedStatement stmt, Syntax syntax) {
        super(stmt, syntax);
    }

    @Override
    public void setDttm(LocalDateTime dttm) throws SQLException {
        super.setString(Dttms.formatSql(dttm));
    }

    @Override
    public void setDt(LocalDate dt) throws SQLException {
        super.setString(Dttms.formatSql(dt));
    }
}
