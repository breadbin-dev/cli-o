package clio.core.tables;

import clio.core.Collections;
import clio.core.tables.ArrayTable;
import org.junit.Test;

import static org.junit.Assert.assertEquals;

public class TestArrayTable {
    private static final String mockHtmlTable = """
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>dttm</th>
      <th>hostname</th>
      <th>used</th>
      <th>size</th>
      <th>mounted_on</th>
      <th>used_perc</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>2024-08-02 13:22</td>
      <td>dxssmtzym001</td>
      <td>2560437168</td>
      <td>3748871708</td>
      <td>/export</td>
      <td>68</td>
    </tr>
    <tr>
      <th>1</th>
      <td>2024-08-02 13:22</td>
      <td>dxssmtzym001</td>
      <td>188899840</td>
      <td>217045696</td>
      <td>/apps/admin</td>
      <td>87</td>
    </tr>
    <tr>
      <th>2</th>
      <td>2024-08-02 13:22</td>
      <td>dxssmtzym001</td>
      <td>188899840</td>
      <td>217045696</td>
      <td>/apps/java</td>
      <td>87</td>
    </tr>
  </tbody>
</table>
""";

    @Test
    public void testHtmlTable() {
        var table = ArrayTable.fromHtml(mockHtmlTable);
        assertEquals(7, table.columns().size());
        var rows = Collections.collect(table.rows());
        assertEquals(3, rows.size());

        assertEquals("/apps/java", table.row(2).readString(table.column("mounted_on")));
    }

}
