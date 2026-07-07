using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeConfigEditableFieldInputViewModelTests
{
    [TestMethod]
    public void InputFieldTracksDirtyStateAndBuildsEditableDraftField()
    {
        var field = new NodeConfigEditableDraftField
        {
            Name = "operator",
            Type = NodeConfigFieldType.Enum,
            Title = "Operator",
            Required = true,
            InputValue = "GT",
            HasInputValue = true,
            EnumValues = ["GT", "LT"],
            Warnings = ["CONFIG_DRAFT_FIELD_REQUIRED_MISSING"],
        };

        var input = new NodeConfigEditableFieldInputViewModel(field);

        Assert.AreEqual("operator", input.Name);
        Assert.AreEqual("Operator", input.DisplayLabel);
        Assert.AreEqual("Enum", input.TypeText);
        Assert.AreEqual("*", input.RequiredText);
        Assert.IsTrue(input.IsEnumInput);
        Assert.IsFalse(input.IsTextInput);
        Assert.IsFalse(input.IsBooleanInput);
        CollectionAssert.AreEqual(
            new[] { "GT", "LT" },
            input.EnumOptions.Select(option => option.Value).ToArray());
        CollectionAssert.AreEqual(
            new[] { "GT", "LT" },
            input.EnumOptions.Select(option => option.DisplayText).ToArray());
        Assert.IsTrue(input.HasWarnings);
        Assert.AreEqual("CONFIG_DRAFT_FIELD_REQUIRED_MISSING", input.WarningText);
        Assert.AreEqual("GT", input.InputValue);
        Assert.IsTrue(input.HasInputValue);
        Assert.IsFalse(input.IsDirty);

        input.InputValue = "LT";

        Assert.IsTrue(input.HasInputValue);
        Assert.IsTrue(input.IsDirty);

        var updated = input.ToEditableDraftField();
        Assert.AreEqual("operator", updated.Name);
        Assert.AreEqual("LT", updated.InputValue);
        Assert.IsTrue(updated.HasInputValue);
        CollectionAssert.AreEqual(
            new[] { "GT", "LT" },
            updated.EnumValues.ToArray());
        CollectionAssert.Contains(
            updated.Warnings.ToArray(),
            "CONFIG_DRAFT_FIELD_REQUIRED_MISSING");
    }

    [TestMethod]
    public void InputFieldExposesViewHelpersForTextAndBooleanInputs()
    {
        var textInput = new NodeConfigEditableFieldInputViewModel(
            new NodeConfigEditableDraftField
            {
                Name = "field",
                Type = NodeConfigFieldType.String,
                InputValue = "amount",
                HasInputValue = true,
            });
        var booleanInput = new NodeConfigEditableFieldInputViewModel(
            new NodeConfigEditableDraftField
            {
                Name = "enabled",
                Type = NodeConfigFieldType.Boolean,
                InputValue = "true",
                HasInputValue = true,
            });

        Assert.AreEqual("field", textInput.DisplayLabel);
        Assert.IsTrue(textInput.IsTextInput);
        Assert.IsFalse(textInput.IsEnumInput);
        Assert.IsFalse(textInput.IsBooleanInput);
        Assert.IsFalse(textInput.HasWarnings);
        Assert.AreEqual(string.Empty, textInput.WarningText);

        Assert.IsFalse(booleanInput.IsTextInput);
        Assert.IsFalse(booleanInput.IsEnumInput);
        Assert.IsTrue(booleanInput.IsBooleanInput);
        CollectionAssert.AreEqual(
            new[] { "true", "false" },
            booleanInput.BooleanValues.ToArray());
        CollectionAssert.AreEqual(
            new[] { "true", "false" },
            booleanInput.BooleanOptions.Select(option => option.Value).ToArray());
        CollectionAssert.AreEqual(
            new[] { "true", "false" },
            booleanInput.BooleanOptions.Select(option => option.DisplayText).ToArray());
    }

    [TestMethod]
    public async Task LocalizesBuiltInFieldTitleAndTypeText()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        var input = new NodeConfigEditableFieldInputViewModel(
            new NodeConfigEditableDraftField
            {
                Name = "rows",
                Type = NodeConfigFieldType.Integer,
                Title = "Rows",
                Required = true,
                InputValue = "3",
                HasInputValue = true,
            },
            "GenerateTestTableNode",
            new DisplayTextFormatter(localizationService));

        Assert.AreEqual("行数", input.DisplayLabel);
        Assert.AreEqual("整数", input.TypeText);
        Assert.AreEqual("*", input.RequiredText);

        var draftField = input.ToEditableDraftField();
        Assert.AreEqual("Rows", draftField.Title);
        Assert.AreEqual("rows", draftField.Name);
    }

    [TestMethod]
    public async Task LocalizesBuiltInEnumAndBooleanOptionDisplayTextWithoutChangingValues()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        var input = new NodeConfigEditableFieldInputViewModel(
            new NodeConfigEditableDraftField
            {
                Name = "operator",
                Type = NodeConfigFieldType.Enum,
                Title = "Operator",
                Required = true,
                InputValue = "GT",
                HasInputValue = true,
                EnumValues = ["EQ", "GT", "IS_NULL"],
            },
            "FilterRowsNode",
            new DisplayTextFormatter(localizationService));

        CollectionAssert.AreEqual(
            new[] { "EQ", "GT", "IS_NULL" },
            input.EnumOptions.Select(option => option.Value).ToArray());
        CollectionAssert.AreEqual(
            new[] { "等于", "大于", "为空" },
            input.EnumOptions.Select(option => option.DisplayText).ToArray());

        input.InputValue = "IS_NULL";
        var draftField = input.ToEditableDraftField();

        Assert.AreEqual("IS_NULL", draftField.InputValue);

        var booleanInput = new NodeConfigEditableFieldInputViewModel(
            new NodeConfigEditableDraftField
            {
                Name = "enabled",
                Type = NodeConfigFieldType.Boolean,
                InputValue = "true",
                HasInputValue = true,
            },
            "FilterRowsNode",
            new DisplayTextFormatter(localizationService));

        CollectionAssert.AreEqual(
            new[] { "true", "false" },
            booleanInput.BooleanOptions.Select(option => option.Value).ToArray());
        CollectionAssert.AreEqual(
            new[] { "是", "否" },
            booleanInput.BooleanOptions.Select(option => option.DisplayText).ToArray());
    }

    [TestMethod]
    public async Task LocalizesAddedBackendNodeEnumOptionDisplayTextWithoutChangingValues()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        var input = new NodeConfigEditableFieldInputViewModel(
            new NodeConfigEditableDraftField
            {
                Name = "target_type",
                Type = NodeConfigFieldType.Enum,
                Title = "Target Type",
                Required = true,
                InputValue = "run_table",
                HasInputValue = true,
                EnumValues = ["run_table", "memory_table", "sqlite"],
            },
            "WriteSelectedColumnsNode",
            new DisplayTextFormatter(localizationService));

        Assert.AreEqual("目标类型", input.DisplayLabel);
        Assert.AreEqual("选项", input.TypeText);
        CollectionAssert.AreEqual(
            new[] { "run_table", "memory_table", "sqlite" },
            input.EnumOptions.Select(option => option.Value).ToArray());
        CollectionAssert.AreEqual(
            new[] { "中转表", "内存表", "SQLite" },
            input.EnumOptions.Select(option => option.DisplayText).ToArray());
    }

    [TestMethod]
    public async Task LocalizedFieldTitleFallsBackToSchemaTitleForUnknownField()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        var input = new NodeConfigEditableFieldInputViewModel(
            new NodeConfigEditableDraftField
            {
                Name = "custom",
                Type = NodeConfigFieldType.String,
                Title = "Custom Field",
                InputValue = "abc",
                HasInputValue = true,
            },
            "CustomPluginNode",
            new DisplayTextFormatter(localizationService));

        Assert.AreEqual("Custom Field", input.DisplayLabel);
        Assert.AreEqual("文本", input.TypeText);
    }
}
