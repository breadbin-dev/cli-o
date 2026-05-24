package clio.core;

import org.w3c.dom.Document;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import javax.xml.parsers.DocumentBuilderFactory;
import java.io.ByteArrayInputStream;
import java.util.ArrayList;
import java.util.List;

import static clio.core.Strings.f;

public class XmlReader {

    public static class Reader {
        private final Node node;

        Reader(Node node) {
            this.node = node;
        }

        public List<Reader> get(String element) {
           return XmlReader.get(node.getChildNodes(), element);
        }

        public List<String> getContent(String element) {
            return XmlReader.getContent(node.getChildNodes(), element);
        }

        public List<String> getContent(String... element) {
            var result = new ArrayList<String>();
            for (var e : element)
                result.addAll(XmlReader.getContent(node.getChildNodes(), e));
            return result;
        }

        public Reader getOne(String element) {
            return XmlReader.getOne(node.getChildNodes(), element);
        }

        public String content() {
            return node.getTextContent();
        }
    }

    public static List<Reader> get(NodeList nodes, String element) {
        var result = new ArrayList<Reader>();
        for (var i = 0; i < nodes.getLength(); i++) {
            var item = nodes.item(i);
            if (element.equals(item.getNodeName()))
                result.add(new Reader(item));
        }
        return result;
    }

    public static List<String> getContent(NodeList nodes, String element) {
        var result = new ArrayList<String>();
        for (var i = 0; i < nodes.getLength(); i++) {
            var item = nodes.item(i);
            if (element.equals(item.getNodeName()))
                result.add(item.getTextContent());
        }
        return result;
    }

    public static Reader getOne(NodeList nodes, String element) {
        var result = get(nodes, element);
        if (result.size() != 1)
            throw new RuntimeException(f("Unexpected [{}] elements of [{}]", result.size(), element));
        return result.getFirst();
    }

    private final Document doc;

    public XmlReader(String xml) {
        try {
            this.doc = DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(new ByteArrayInputStream(xml.getBytes()));
            doc.getDocumentElement().normalize();
        } catch (Exception ex) {
            throw new RuntimeException(ex);
        }
    }

    public List<Reader> get(String element) {
        var list = doc.getElementsByTagName(element);
        return get(list, element);
    }

    public Reader getOne(String element) {
        return getOne(doc.getElementsByTagName(element), element);
    }
}
