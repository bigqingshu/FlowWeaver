using System.Linq;
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
    }
}
