using System;
using System.Collections.Generic;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class NodeConfigEditableFieldInputViewModel : ViewModelBase
{
    private static readonly IReadOnlyList<string> BooleanInputValues =
        ["true", "false"];

    public NodeConfigEditableFieldInputViewModel(
        NodeConfigEditableDraftField field,
        string nodeType = "",
        DisplayTextFormatter? displayTextFormatter = null)
    {
        DisplayTextFormatter = displayTextFormatter ?? DisplayTextFormatter.Invariant;
        NodeType = nodeType;
        Name = field.Name;
        Type = field.Type;
        Title = field.Title;
        Required = field.Required;
        OriginalInputValue = field.InputValue;
        InputValue = field.InputValue;
        OriginalHasInputValue = field.HasInputValue;
        HasInputValue = field.HasInputValue;
        EnumValues = field.EnumValues;
        Warnings = field.Warnings;
    }

    public DisplayTextFormatter DisplayTextFormatter { get; }

    public string NodeType { get; }

    public string Name { get; }

    public NodeConfigFieldType Type { get; }

    public string? Title { get; }

    public bool Required { get; }

    public string OriginalInputValue { get; }

    public bool OriginalHasInputValue { get; }

    public IReadOnlyList<string> EnumValues { get; }

    public IReadOnlyList<string> Warnings { get; }

    public string DisplayLabel =>
        DisplayTextFormatter.FormatNodeConfigFieldTitle(NodeType, Name, Title);

    public string TypeText =>
        DisplayTextFormatter.FormatNodeConfigFieldType(Type.ToString());

    public string RequiredText => Required ? "*" : string.Empty;

    public bool IsTextInput =>
        Type is NodeConfigFieldType.String
            or NodeConfigFieldType.Integer
            or NodeConfigFieldType.Number;

    public bool IsEnumInput => Type == NodeConfigFieldType.Enum;

    public bool IsBooleanInput => Type == NodeConfigFieldType.Boolean;

    public IReadOnlyList<string> BooleanValues => BooleanInputValues;

    public bool HasWarnings => Warnings.Count > 0;

    public string WarningText => string.Join(", ", Warnings);

    public bool IsDirty =>
        !string.Equals(InputValue, OriginalInputValue, StringComparison.Ordinal)
        || HasInputValue != OriginalHasInputValue;

    [ObservableProperty]
    private string inputValue = string.Empty;

    [ObservableProperty]
    private bool hasInputValue;

    public NodeConfigEditableDraftField ToEditableDraftField()
    {
        return new NodeConfigEditableDraftField
        {
            Name = Name,
            Type = Type,
            Title = Title,
            Required = Required,
            InputValue = InputValue,
            HasInputValue = HasInputValue,
            EnumValues = EnumValues,
            Warnings = Warnings,
        };
    }

    partial void OnInputValueChanged(string value)
    {
        HasInputValue = true;
        OnPropertyChanged(nameof(IsDirty));
    }

    partial void OnHasInputValueChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDirty));
    }

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(DisplayLabel));
        OnPropertyChanged(nameof(TypeText));
    }
}
