using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Diagnostics.CodeAnalysis;
using System.Linq;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

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
        OriginalInputValue = field.InputValue ?? string.Empty;
        InputValue = OriginalInputValue;
        OriginalHasInputValue = field.HasInputValue;
        HasInputValue = field.HasInputValue;
        EnumValues = field.EnumValues;
        ItemType = field.ItemType;
        OriginalStringArrayValues = field.StringArrayValues.ToArray();
        Warnings = field.Warnings;
        foreach (var value in field.StringArrayValues)
        {
            AddStringArrayItemCore(value, markInputPresent: false);
        }
    }

    public DisplayTextFormatter DisplayTextFormatter { get; }

    public string NodeType { get; }

    public string Name { get; }

    public NodeConfigFieldType Type { get; }

    public string? Title { get; }

    public bool Required { get; }

    public string OriginalInputValue { get; private set; }

    public bool OriginalHasInputValue { get; private set; }

    public IReadOnlyList<string> EnumValues { get; }

    public string? ItemType { get; }

    public IReadOnlyList<string> OriginalStringArrayValues { get; private set; }

    public ObservableCollection<NodeConfigStringArrayItemViewModel> StringArrayItems { get; } =
        new();

    public IReadOnlyList<string> Warnings { get; }

    public string DisplayLabel =>
        DisplayTextFormatter.FormatNodeConfigFieldTitle(NodeType, Name, Title);

    public string TypeText =>
        DisplayTextFormatter.FormatNodeConfigFieldType(
            IsStringArrayInput ? "string_array" : Type.ToString());

    public string RequiredText => Required ? "*" : string.Empty;

    public string AddStringArrayItemText =>
        DisplayTextFormatter.FormatNodeConfigArrayAddItem();

    public bool IsTextInput =>
        Type is NodeConfigFieldType.String
            or NodeConfigFieldType.Integer
            or NodeConfigFieldType.Number;

    public bool IsEnumInput => Type == NodeConfigFieldType.Enum;

    public bool IsBooleanInput => Type == NodeConfigFieldType.Boolean;

    public bool IsStringArrayInput =>
        Type == NodeConfigFieldType.Array
        && string.Equals(ItemType, "string", StringComparison.Ordinal);

    public IReadOnlyList<string> BooleanValues => BooleanInputValues;

    public IReadOnlyList<NodeConfigOptionItemViewModel> EnumOptions =>
        EnumValues
            .Select(value => new NodeConfigOptionItemViewModel(
                value,
                DisplayTextFormatter.FormatNodeConfigOptionValue(NodeType, Name, value)))
            .ToArray();

    public IReadOnlyList<NodeConfigOptionItemViewModel> BooleanOptions =>
        BooleanInputValues
            .Select(value => new NodeConfigOptionItemViewModel(
                value,
                DisplayTextFormatter.FormatNodeConfigOptionValue(NodeType, Name, value)))
            .ToArray();

    public bool HasWarnings => Warnings.Count > 0;

    public string WarningText => string.Join(", ", Warnings);

    public bool IsDirty =>
        HasInputValue != OriginalHasInputValue
        || (IsStringArrayInput
            ? !OriginalStringArrayValues.SequenceEqual(
                StringArrayItems.Select(item => item.Value),
                StringComparer.Ordinal)
            : !string.Equals(
                InputValue,
                OriginalInputValue,
                StringComparison.Ordinal));

    private string inputValue = string.Empty;

    [AllowNull]
    public string InputValue
    {
        get => inputValue;
        set
        {
            var normalized = value ?? string.Empty;
            if (!SetProperty(ref inputValue, normalized))
            {
                return;
            }

            HasInputValue = true;
            OnPropertyChanged(nameof(IsDirty));
        }
    }

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
            ItemType = ItemType,
            StringArrayValues = StringArrayItems
                .Select(item => item.Value)
                .ToArray(),
            Warnings = Warnings,
        };
    }

    public void AcceptChanges()
    {
        OriginalInputValue = InputValue;
        OriginalHasInputValue = HasInputValue;
        OriginalStringArrayValues = StringArrayItems
            .Select(item => item.Value)
            .ToArray();
        OnPropertyChanged(nameof(IsDirty));
    }

    public void ReplaceStringArrayValues(
        IEnumerable<string> values,
        bool hasInputValue)
    {
        StringArrayItems.Clear();
        foreach (var value in values)
        {
            AddStringArrayItemCore(value, markInputPresent: false);
        }

        HasInputValue = hasInputValue;
        UpdateStringArrayMoveAvailability();
        OnPropertyChanged(nameof(IsDirty));
    }

    [RelayCommand]
    private void AddStringArrayItem()
    {
        AddStringArrayItemCore(string.Empty, markInputPresent: true);
    }

    private void AddStringArrayItemCore(string value, bool markInputPresent)
    {
        StringArrayItems.Add(
            new NodeConfigStringArrayItemViewModel(
                value,
                DisplayTextFormatter,
                HandleStringArrayItemValueChanged,
                RemoveStringArrayItem,
                MoveStringArrayItemUp,
                MoveStringArrayItemDown));
        if (markInputPresent)
        {
            HasInputValue = true;
        }

        UpdateStringArrayMoveAvailability();
        OnPropertyChanged(nameof(IsDirty));
    }

    private void HandleStringArrayItemValueChanged(
        NodeConfigStringArrayItemViewModel item)
    {
        HasInputValue = true;
        OnPropertyChanged(nameof(IsDirty));
    }

    private void RemoveStringArrayItem(NodeConfigStringArrayItemViewModel item)
    {
        if (!StringArrayItems.Remove(item))
        {
            return;
        }

        HasInputValue = true;
        UpdateStringArrayMoveAvailability();
        OnPropertyChanged(nameof(IsDirty));
    }

    private void MoveStringArrayItemUp(NodeConfigStringArrayItemViewModel item)
    {
        MoveStringArrayItem(item, -1);
    }

    private void MoveStringArrayItemDown(NodeConfigStringArrayItemViewModel item)
    {
        MoveStringArrayItem(item, 1);
    }

    private void MoveStringArrayItem(
        NodeConfigStringArrayItemViewModel item,
        int offset)
    {
        var currentIndex = StringArrayItems.IndexOf(item);
        var targetIndex = currentIndex + offset;
        if (currentIndex < 0
            || targetIndex < 0
            || targetIndex >= StringArrayItems.Count)
        {
            return;
        }

        StringArrayItems.Move(currentIndex, targetIndex);
        HasInputValue = true;
        UpdateStringArrayMoveAvailability();
        OnPropertyChanged(nameof(IsDirty));
    }

    private void UpdateStringArrayMoveAvailability()
    {
        for (var index = 0; index < StringArrayItems.Count; index++)
        {
            StringArrayItems[index].SetMoveAvailability(
                moveUpAvailable: index > 0,
                moveDownAvailable: index < StringArrayItems.Count - 1);
        }
    }

    partial void OnHasInputValueChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDirty));
    }

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(DisplayLabel));
        OnPropertyChanged(nameof(TypeText));
        OnPropertyChanged(nameof(EnumOptions));
        OnPropertyChanged(nameof(BooleanOptions));
        OnPropertyChanged(nameof(AddStringArrayItemText));
        foreach (var item in StringArrayItems)
        {
            item.RefreshLocalizedText();
        }
    }
}
