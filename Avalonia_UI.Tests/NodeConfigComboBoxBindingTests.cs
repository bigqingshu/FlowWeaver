using System.Text.Json;
using Avalonia.Controls;
using Avalonia.Controls.Primitives;
using Avalonia.Data;
using Avalonia_UI.Models;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeConfigComboBoxBindingTests
{
    [TestMethod]
    public void SelectedValueBindingShowsResolvedDefaultWithoutUserInteraction()
    {
        using var schemaDocument = JsonDocument.Parse(
            """
            {
              "type": "object",
              "properties": {
                "operator": {
                  "type": "enum",
                  "required": true,
                  "enum": ["EQ", "GT"]
                }
              }
            }
            """);
        var schemaResult = NodeConfigSchemaParser.Parse(
            "1.0",
            schemaDocument.RootElement);
        Assert.IsNotNull(schemaResult.Schema);
        var draft = NodeConfigDraftBuilder.Build(
            """{"nodes":[{"node_instance_id":"filter","config":{}}]}""",
            "filter",
            schemaResult.Schema);
        var editableField = NodeConfigEditableDraftBuilder.Build(draft).Fields[0];
        var input = new NodeConfigEditableFieldInputViewModel(
            editableField);
        var comboBox = new ComboBox
        {
            DataContext = input,
            ItemsSource = input.EnumOptions,
            SelectedValueBinding = new Binding(
                nameof(NodeConfigOptionItemViewModel.Value)),
        };
        using var binding = comboBox.Bind(
            SelectingItemsControl.SelectedValueProperty,
            new Binding(nameof(NodeConfigEditableFieldInputViewModel.InputValue))
            {
                Mode = BindingMode.TwoWay,
            });

        Assert.IsNotNull(comboBox.SelectedItem);
        Assert.AreEqual(
            "EQ",
            ((NodeConfigOptionItemViewModel)comboBox.SelectedItem).Value);
    }
}
