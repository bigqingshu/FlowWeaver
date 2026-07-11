using System.Linq;
using System.Text.Json;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeConfigDraftBuilderTests
{
    [TestMethod]
    public void BuildCreatesDraftForSelectedNodeConfig()
    {
        var schema = ParseSchema(
            """
            {
              "type": "object",
              "properties": {
                "field": {"type": "string", "title": "Field", "required": true},
                "operator": {"type": "enum", "title": "Operator", "enum": ["GT", "LT"]},
                "limit": {"type": "integer", "title": "Limit", "default": 10},
                "columns": {"type": "array", "items": {"type": "string"}}
              }
            }
            """);
        var draft = NodeConfigDraftBuilder.Build(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "source",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0"
                },
                {
                  "node_instance_id": "filter",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "config": {
                    "field": "amount",
                    "operator": "GT"
                  }
                }
              ],
              "connections": []
            }
            """,
            "filter",
            schema);

        Assert.IsTrue(draft.IsSupported);
        Assert.AreEqual(NodeConfigDraftStatus.Supported, draft.Status);
        Assert.AreEqual("filter", draft.NodeInstanceId);
        Assert.HasCount(4, draft.Fields);
        Assert.IsEmpty(draft.Warnings);

        var field = draft.Fields.Single(item => item.Name == "field");
        Assert.AreEqual(NodeConfigFieldType.String, field.Type);
        Assert.AreEqual("Field", field.Title);
        Assert.IsTrue(field.Required);
        Assert.IsTrue(field.IsEditable);
        Assert.AreEqual("amount", field.CurrentValue?.GetString());
        Assert.IsTrue(field.HasCurrentValue);

        var limit = draft.Fields.Single(item => item.Name == "limit");
        Assert.IsFalse(limit.HasCurrentValue);
        Assert.AreEqual(10, limit.DefaultValue?.GetInt32());
        Assert.IsTrue(limit.IsEditable);

        var columns = draft.Fields.Single(item => item.Name == "columns");
        Assert.IsTrue(columns.IsEditable);
        Assert.AreEqual("string", columns.ItemType);
        CollectionAssert.DoesNotContain(
            columns.Warnings.ToArray(),
            "CONFIG_DRAFT_FIELD_JSON_FALLBACK");
    }

    [TestMethod]
    public void BuildOnlyEnablesValidStringArrayFields()
    {
        var schema = ParseSchema(
            """
            {
              "type": "object",
              "properties": {
                "names": {"type": "array", "items": {"type": "string"}},
                "objects": {"type": "array", "items": {"type": "object"}},
                "unknown": {"type": "array"},
                "malformed": {"type": "array", "items": {"type": "string"}}
              }
            }
            """);

        var draft = NodeConfigDraftBuilder.Build(
            """
            {
              "nodes": [
                {
                  "node_instance_id": "node",
                  "config": {
                    "names": ["first", "second"],
                    "objects": [{"name": "first"}],
                    "unknown": [1],
                    "malformed": ["first", 2]
                  }
                }
              ]
            }
            """,
            "node",
            schema);

        Assert.IsTrue(draft.Fields.Single(field => field.Name == "names").IsEditable);
        Assert.IsFalse(draft.Fields.Single(field => field.Name == "objects").IsEditable);
        Assert.IsFalse(draft.Fields.Single(field => field.Name == "unknown").IsEditable);
        Assert.IsFalse(draft.Fields.Single(field => field.Name == "malformed").IsEditable);
        CollectionAssert.Contains(
            draft.Fields.Single(field => field.Name == "malformed").Warnings.ToArray(),
            "CONFIG_DRAFT_FIELD_JSON_FALLBACK");
    }

    [TestMethod]
    public void BuildMarksMissingRequiredField()
    {
        var schema = ParseSchema(
            """
            {
              "type": "object",
              "properties": {
                "field": {"type": "string", "required": true}
              }
            }
            """);

        var draft = NodeConfigDraftBuilder.Build(
            """
            {
              "nodes": [
                {"node_instance_id": "filter", "config": {}}
              ]
            }
            """,
            "filter",
            schema);

        var field = draft.Fields.Single();
        CollectionAssert.Contains(
            field.Warnings.ToArray(),
            "CONFIG_DRAFT_FIELD_REQUIRED_MISSING");
    }

    [TestMethod]
    public void BuildReturnsJsonInvalidWhenDraftJsonCannotParse()
    {
        var draft = NodeConfigDraftBuilder.Build(
            "{",
            "filter",
            ParseSchema("""{"type":"object","properties":{}}"""));

        Assert.IsFalse(draft.IsSupported);
        Assert.AreEqual(NodeConfigDraftStatus.JsonInvalid, draft.Status);
        CollectionAssert.Contains(
            draft.Warnings.ToArray(),
            "CONFIG_DRAFT_JSON_INVALID");
    }

    [TestMethod]
    public void BuildReturnsNodeNotFoundWhenSelectedNodeIsMissing()
    {
        var draft = NodeConfigDraftBuilder.Build(
            """{"nodes":[{"node_instance_id":"source"}]}""",
            "filter",
            ParseSchema("""{"type":"object","properties":{}}"""));

        Assert.IsFalse(draft.IsSupported);
        Assert.AreEqual(NodeConfigDraftStatus.NodeNotFound, draft.Status);
        CollectionAssert.Contains(
            draft.Warnings.ToArray(),
            "CONFIG_DRAFT_NODE_NOT_FOUND");
    }

    [TestMethod]
    public void BuildReturnsSchemaUnsupportedWithoutParsingWorkflowJson()
    {
        var draft = NodeConfigDraftBuilder.Build(
            "{",
            "filter",
            new NodeConfigSchemaDescriptor { IsSupported = false });

        Assert.IsFalse(draft.IsSupported);
        Assert.AreEqual(NodeConfigDraftStatus.SchemaUnsupported, draft.Status);
        CollectionAssert.Contains(
            draft.Warnings.ToArray(),
            "CONFIG_DRAFT_SCHEMA_UNSUPPORTED");
    }

    private static NodeConfigSchemaDescriptor ParseSchema(string schemaJson)
    {
        using var document = JsonDocument.Parse(schemaJson);
        var result = NodeConfigSchemaParser.Parse("1.0", document.RootElement);
        Assert.IsTrue(result.IsSupported);
        Assert.IsNotNull(result.Schema);
        return result.Schema;
    }
}
