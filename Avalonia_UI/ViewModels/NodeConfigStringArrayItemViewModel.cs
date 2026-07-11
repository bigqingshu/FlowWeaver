using System;
using Avalonia_UI.Localization;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class NodeConfigStringArrayItemViewModel : ViewModelBase
{
    private readonly Action<NodeConfigStringArrayItemViewModel> _valueChanged;
    private readonly Action<NodeConfigStringArrayItemViewModel> _remove;
    private readonly Action<NodeConfigStringArrayItemViewModel> _moveUp;
    private readonly Action<NodeConfigStringArrayItemViewModel> _moveDown;

    public NodeConfigStringArrayItemViewModel(
        string value,
        DisplayTextFormatter displayTextFormatter,
        Action<NodeConfigStringArrayItemViewModel> valueChanged,
        Action<NodeConfigStringArrayItemViewModel> remove,
        Action<NodeConfigStringArrayItemViewModel> moveUp,
        Action<NodeConfigStringArrayItemViewModel> moveDown)
    {
        DisplayTextFormatter = displayTextFormatter;
        _valueChanged = valueChanged;
        _remove = remove;
        _moveUp = moveUp;
        _moveDown = moveDown;
        this.value = value;
    }

    public DisplayTextFormatter DisplayTextFormatter { get; }

    public string RemoveText => DisplayTextFormatter.FormatNodeConfigArrayRemoveItem();

    public string MoveUpText => DisplayTextFormatter.FormatNodeConfigArrayMoveUp();

    public string MoveDownText => DisplayTextFormatter.FormatNodeConfigArrayMoveDown();

    [ObservableProperty]
    private string value = string.Empty;

    [ObservableProperty]
    private bool canMoveUp;

    [ObservableProperty]
    private bool canMoveDown;

    [RelayCommand]
    private void Remove()
    {
        _remove(this);
    }

    private bool CanMoveUpItem()
    {
        return CanMoveUp;
    }

    [RelayCommand(CanExecute = nameof(CanMoveUpItem))]
    private void MoveUp()
    {
        _moveUp(this);
    }

    private bool CanMoveDownItem()
    {
        return CanMoveDown;
    }

    [RelayCommand(CanExecute = nameof(CanMoveDownItem))]
    private void MoveDown()
    {
        _moveDown(this);
    }

    public void SetMoveAvailability(bool moveUpAvailable, bool moveDownAvailable)
    {
        CanMoveUp = moveUpAvailable;
        CanMoveDown = moveDownAvailable;
    }

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(RemoveText));
        OnPropertyChanged(nameof(MoveUpText));
        OnPropertyChanged(nameof(MoveDownText));
    }

    partial void OnValueChanged(string value)
    {
        _valueChanged(this);
    }

    partial void OnCanMoveUpChanged(bool value)
    {
        MoveUpCommand.NotifyCanExecuteChanged();
    }

    partial void OnCanMoveDownChanged(bool value)
    {
        MoveDownCommand.NotifyCanExecuteChanged();
    }
}
