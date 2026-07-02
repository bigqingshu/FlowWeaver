using System;
using System.Collections.Generic;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class NodeConfigEditableFieldInputViewModel : ViewModelBase
{
    public NodeConfigEditableFieldInputViewModel(NodeConfigEditableDraftField field)
    {
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

    public string Name { get; }

    public NodeConfigFieldType Type { get; }

    public string? Title { get; }

    public bool Required { get; }

    public string OriginalInputValue { get; }

    public bool OriginalHasInputValue { get; }

    public IReadOnlyList<string> EnumValues { get; }

    public IReadOnlyList<string> Warnings { get; }

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
}
