using System.Linq;
using System.Text.Json;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeConfigEditableDraftConfigBuilderTests
{
    [TestMethod]
    public void BuildCreatesConfigJsonFromEditableFields()
    {
        var draft = new NodeConfigEditableDraft
        {
            NodeInstanceId = "filter",
            Fields =
            [
                Field("field", NodeConfigFieldType.String, "amount"),
                Field("limit", NodeConfigFieldType.Integer, "3"),
                Field("ratio", NodeConfigFieldType.Number, "1.5"),
                Field("enabled", NodeConfigFieldType.Boolean, "false"),
                Field(
                    "operator",
                    NodeConfigFieldType.Enum,
                    "GT",
                    enumValues: ["GT", "LT"]),
            ],
        };

        var result = NodeConfigEditableDraftConfigBuilder.Build(draft);

        Assert.IsTrue(result.Succeeded);
        Assert.AreEqual(
            NodeConfigEditableDraftConfigBuildStatus.Succeeded,
            result.Status);
        Assert.IsEmpty(result.Warnings);
        Assert.IsEmpty(result.FieldErrors);

        using var document = JsonDocument.Parse(result.ConfigJson);
        var root = document.RootElement;
        Assert.AreEqual("amount", root.GetProperty("field").GetString());
        Assert.AreEqual(3, root.GetProperty("limit").GetInt64());
        Assert.AreEqual(1.5m, root.GetProperty("ratio").GetDecimal());
        Assert.IsFalse(root.GetProperty("enabled").GetBoolean());
        Assert.AreEqual("GT", root.GetProperty("operator").GetString());
    }

    [TestMethod]
    public void BuildOmitsMissingOptionalFieldsEvenWhenInputTextIsStale()
    {
        var draft = new NodeConfigEditableDraft
        {
            NodeInstanceId = "filter",
            Fields =
            [
                Field(
                    "optional_field",
                    NodeConfigFieldType.String,
                    "stale value",
                    hasInputValue: false),
                Field(
                    "required_field",
                    NodeConfigFieldType.String,
                    "amount",
                    required: true),
            ],
        };

        var result = NodeConfigEditableDraftConfigBuilder.Build(draft);

        Assert.IsTrue(result.Succeeded);
        using var document = JsonDocument.Parse(result.ConfigJson);
        Assert.IsFalse(document.RootElement.TryGetProperty("optional_field", out _));
        Assert.AreEqual(
            "amount",
            document.RootElement.GetProperty("required_field").GetString());
    }

    [TestMethod]
    public void BuildPreservesExplicitEmptyStringWhenFieldHasInputValue()
    {
        var draft = new NodeConfigEditableDraft
        {
            NodeInstanceId = "filter",
            Fields =
            [
                Field(
                    "field",
                    NodeConfigFieldType.String,
                    string.Empty,
                    hasInputValue: true),
            ],
        };

        var result = NodeConfigEditableDraftConfigBuilder.Build(draft);

        Assert.IsTrue(result.Succeeded);
        using var document = JsonDocument.Parse(result.ConfigJson);
        Assert.AreEqual(string.Empty, document.RootElement.GetProperty("field").GetString());
    }

    [TestMethod]
    public void BuildNormalizesNullStringInputToEmptyString()
    {
        var draft = new NodeConfigEditableDraft
        {
            NodeInstanceId = "filter",
            Fields =
            [
                Field(
                    "field",
                    NodeConfigFieldType.String,
                    null!,
                    hasInputValue: true),
            ],
        };

        var result = NodeConfigEditableDraftConfigBuilder.Build(draft);

        Assert.IsTrue(result.Succeeded);
        using var document = JsonDocument.Parse(result.ConfigJson);
        Assert.AreEqual(string.Empty, document.RootElement.GetProperty("field").GetString());
    }

    [TestMethod]
    public void BuildRejectsRequiredEmptyField()
    {
        var draft = new NodeConfigEditableDraft
        {
            NodeInstanceId = "filter",
            Fields =
            [
                Field(
                    "field",
                    NodeConfigFieldType.String,
                    string.Empty,
                    required: true,
                    hasInputValue: false),
            ],
        };

        var result = NodeConfigEditableDraftConfigBuilder.Build(draft);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(
            NodeConfigEditableDraftConfigBuildStatus.FieldInvalid,
            result.Status);
        Assert.AreEqual("{}", result.ConfigJson);
        var error = result.FieldErrors.Single();
        Assert.AreEqual("field", error.FieldName);
        Assert.AreEqual("EDITABLE_CONFIG_FIELD_REQUIRED_EMPTY", error.Warning);
        CollectionAssert.Contains(
            result.Warnings.ToArray(),
            "EDITABLE_CONFIG_FIELD_REQUIRED_EMPTY");
    }

    [TestMethod]
    public void BuildRejectsInvalidScalarInputs()
    {
        var draft = new NodeConfigEditableDraft
        {
            NodeInstanceId = "filter",
            Fields =
            [
                Field("limit", NodeConfigFieldType.Integer, "1.2"),
                Field("ratio", NodeConfigFieldType.Number, "abc"),
                Field("enabled", NodeConfigFieldType.Boolean, "yes"),
                Field(
                    "operator",
                    NodeConfigFieldType.Enum,
                    "NE",
                    enumValues: ["GT", "LT"]),
            ],
        };

        var result = NodeConfigEditableDraftConfigBuilder.Build(draft);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(
            NodeConfigEditableDraftConfigBuildStatus.FieldInvalid,
            result.Status);
        Assert.HasCount(4, result.FieldErrors);
        CollectionAssert.Contains(
            result.FieldErrors.Select(error => error.Warning).ToArray(),
            "EDITABLE_CONFIG_FIELD_INTEGER_INVALID");
        CollectionAssert.Contains(
            result.FieldErrors.Select(error => error.Warning).ToArray(),
            "EDITABLE_CONFIG_FIELD_NUMBER_INVALID");
        CollectionAssert.Contains(
            result.FieldErrors.Select(error => error.Warning).ToArray(),
            "EDITABLE_CONFIG_FIELD_BOOLEAN_INVALID");
        CollectionAssert.Contains(
            result.FieldErrors.Select(error => error.Warning).ToArray(),
            "EDITABLE_CONFIG_FIELD_ENUM_INVALID");
    }

    [TestMethod]
    public void BuildRejectsNullNonStringScalarInputsWithoutThrowing()
    {
        var draft = new NodeConfigEditableDraft
        {
            NodeInstanceId = "filter",
            Fields =
            [
                Field("limit", NodeConfigFieldType.Integer, null!),
                Field("ratio", NodeConfigFieldType.Number, null!),
                Field("enabled", NodeConfigFieldType.Boolean, null!),
                Field(
                    "operator",
                    NodeConfigFieldType.Enum,
                    null!,
                    enumValues: ["GT", "LT"]),
            ],
        };

        var result = NodeConfigEditableDraftConfigBuilder.Build(draft);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(
            NodeConfigEditableDraftConfigBuildStatus.FieldInvalid,
            result.Status);
        CollectionAssert.AreEquivalent(
            new[]
            {
                "EDITABLE_CONFIG_FIELD_INTEGER_INVALID",
                "EDITABLE_CONFIG_FIELD_NUMBER_INVALID",
                "EDITABLE_CONFIG_FIELD_BOOLEAN_INVALID",
                "EDITABLE_CONFIG_FIELD_ENUM_INVALID",
            },
            result.FieldErrors.Select(error => error.Warning).ToArray());
    }

    [TestMethod]
    public void BuildPreservesStringArrayOrderAndExplicitEmptyArray()
    {
        var draft = new NodeConfigEditableDraft
        {
            NodeInstanceId = "shared",
            Fields =
            [
                Field(
                    "export_names",
                    NodeConfigFieldType.Array,
                    "[\"orders\",\"customers\"]",
                    required: true,
                    itemType: "string",
                    stringArrayValues: ["orders", "customers"]),
                Field(
                    "selected_members",
                    NodeConfigFieldType.Array,
                    "[]",
                    itemType: "string",
                    stringArrayValues: []),
            ],
        };

        var result = NodeConfigEditableDraftConfigBuilder.Build(draft);

        Assert.IsTrue(result.Succeeded);
        using var document = JsonDocument.Parse(result.ConfigJson);
        CollectionAssert.AreEqual(
            new[] { "orders", "customers" },
            document.RootElement
                .GetProperty("export_names")
                .EnumerateArray()
                .Select(item => item.GetString())
                .ToArray());
        Assert.AreEqual(
            0,
            document.RootElement.GetProperty("selected_members").GetArrayLength());
    }

    [TestMethod]
    public void BuildRejectsEmptyStringArrayItemWithoutDroppingIt()
    {
        var draft = new NodeConfigEditableDraft
        {
            NodeInstanceId = "shared",
            Fields =
            [
                Field(
                    "export_names",
                    NodeConfigFieldType.Array,
                    "[\"orders\",\"\"]",
                    required: true,
                    itemType: "string",
                    stringArrayValues: ["orders", ""]),
            ],
        };

        var result = NodeConfigEditableDraftConfigBuilder.Build(draft);

        Assert.IsFalse(result.Succeeded);
        var error = result.FieldErrors.Single();
        Assert.AreEqual("export_names", error.FieldName);
        Assert.AreEqual(
            "EDITABLE_CONFIG_FIELD_STRING_ARRAY_ITEM_EMPTY",
            error.Warning);
    }

    [TestMethod]
    public void BuildRejectsUnsupportedEditableFieldType()
    {
        var draft = new NodeConfigEditableDraft
        {
            NodeInstanceId = "filter",
            Fields =
            [
                Field("metadata", NodeConfigFieldType.Object, "{}", hasInputValue: true),
            ],
        };

        var result = NodeConfigEditableDraftConfigBuilder.Build(draft);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(
            NodeConfigEditableDraftConfigBuildStatus.FieldInvalid,
            result.Status);
        var error = result.FieldErrors.Single();
        Assert.AreEqual("metadata", error.FieldName);
        Assert.AreEqual("EDITABLE_CONFIG_FIELD_TYPE_UNSUPPORTED", error.Warning);
    }

    [TestMethod]
    public void BuildReturnsDraftUnsupportedWhenThereAreNoFields()
    {
        var draft = new NodeConfigEditableDraft
        {
            NodeInstanceId = "filter",
            Warnings = ["CONFIG_DRAFT_JSON_INVALID"],
        };

        var result = NodeConfigEditableDraftConfigBuilder.Build(draft);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(
            NodeConfigEditableDraftConfigBuildStatus.DraftUnsupported,
            result.Status);
        CollectionAssert.Contains(
            result.Warnings.ToArray(),
            "CONFIG_DRAFT_JSON_INVALID");
        CollectionAssert.Contains(
            result.Warnings.ToArray(),
            "EDITABLE_CONFIG_NO_EDITABLE_FIELDS");
    }

    private static NodeConfigEditableDraftField Field(
        string name,
        NodeConfigFieldType type,
        string inputValue,
        bool required = false,
        bool hasInputValue = true,
        string[]? enumValues = null,
        string? itemType = null,
        string[]? stringArrayValues = null)
    {
        return new NodeConfigEditableDraftField
        {
            Name = name,
            Type = type,
            InputValue = inputValue,
            Required = required,
            HasInputValue = hasInputValue,
            EnumValues = enumValues ?? [],
            ItemType = itemType,
            StringArrayValues = stringArrayValues ?? [],
        };
    }
}
