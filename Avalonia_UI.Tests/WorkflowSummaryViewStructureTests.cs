using System;
using System.IO;
using System.Linq;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowSummaryViewStructureTests
{
    [TestMethod]
    public void NodeTemplateShowsEditorStatusAsReadOnlyText()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "Text=\"{Binding NodeEditorStatusText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding ConfigJson}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding SelectedNodeConfigDraftSummaryText}\"");
        StringAssert.Contains(xaml, "SelectedItem=\"{Binding SelectedWorkflowDefinitionNode}\"");
        StringAssert.Contains(xaml, "RowDefinitions=\"Auto,Auto,Auto,Auto\"");
        Assert.IsFalse(xaml.Contains("NodeEditorStatusText}\" Command=", StringComparison.Ordinal));
    }

    [TestMethod]
    public void NodeTemplateDoesNotIntroduceNodeEditingActions()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        Assert.IsFalse(xaml.Contains("EditNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("ConfigureNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("OpenNodeEditor", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("SaveNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("ListNodeDefinitionsAsync", StringComparison.Ordinal));
    }

    [TestMethod]
    public void NodeConfigEditorBindsToInputFieldsAndApplyCommand()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(
            xaml,
            "ItemsSource=\"{Binding SelectedNodeConfigEditableInputFields}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding ApplySelectedNodeConfigDraftCommand}\"");
        StringAssert.Contains(
            xaml,
            "x:DataType=\"vm:NodeConfigEditableFieldInputViewModel\"");
        StringAssert.Contains(xaml, "Text=\"{Binding InputValue, Mode=TwoWay");
        StringAssert.Contains(xaml, "SelectedItem=\"{Binding InputValue, Mode=TwoWay}\"");
    }

    [TestMethod]
    public void NodeConfigEditorUsesViewHelperBindingsWithoutConverters()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(
            xaml,
            "IsVisible=\"{Binding HasSelectedNodeConfigEditableInputFields}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding DisplayLabel}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding TypeText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding RequiredText}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsTextInput}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsEnumInput}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsBooleanInput}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding BooleanValues}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding WarningText}\"");
        Assert.IsFalse(xaml.Contains("Converter=", StringComparison.Ordinal));
    }

    [TestMethod]
    public void StructuredEditFormsBindToDraftInputsAndCommands()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "Text=\"{Binding StructuredEditSectionText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NodeInstanceIdText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NodeTypeText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NodeVersionText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding DisplayNameText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding ConfigJsonText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftNodeInstanceId, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftNodeType, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftNodeVersion, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftNodeDisplayName, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftNodeConfigJson, Mode=TwoWay");
        StringAssert.Contains(
            xaml,
            "ItemsSource=\"{Binding NodeDefinitions}\"");
        StringAssert.Contains(
            xaml,
            "SelectedItem=\"{Binding SelectedNewDraftNodeDefinition, Mode=TwoWay}\"");
        StringAssert.Contains(
            xaml,
            "x:DataType=\"vm:NodeDefinitionListItemViewModel\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding AddWorkflowDefinitionDraftNodeCommand}\"");
        StringAssert.Contains(
            xaml,
            "Text=\"{Binding SelectedWorkflowDefinitionDraftNodeInstanceId, Mode=TwoWay");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding DeleteWorkflowDefinitionDraftNodeCommand}\"");

        StringAssert.Contains(xaml, "Text=\"{Binding ConnectionIdText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding SourceNodeText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding SourcePortText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding TargetNodeText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding TargetPortText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftConnectionId, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftConnectionSourceNodeId, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftConnectionSourcePort, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftConnectionTargetNodeId, Mode=TwoWay");
        StringAssert.Contains(xaml, "Text=\"{Binding NewDraftConnectionTargetPort, Mode=TwoWay");
        StringAssert.Contains(
            xaml,
            "ItemsSource=\"{Binding WorkflowDefinitionDraftStructure.Nodes}\"");
        StringAssert.Contains(
            xaml,
            "SelectedItem=\"{Binding SelectedNewDraftConnectionSourceNode, Mode=TwoWay}\"");
        StringAssert.Contains(
            xaml,
            "SelectedItem=\"{Binding SelectedNewDraftConnectionTargetNode, Mode=TwoWay}\"");
        StringAssert.Contains(
            xaml,
            "x:DataType=\"models:WorkflowDefinitionDraftNode\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding AddWorkflowDefinitionDraftConnectionCommand}\"");
        StringAssert.Contains(
            xaml,
            "Text=\"{Binding SelectedWorkflowDefinitionDraftConnectionId, Mode=TwoWay");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding DeleteWorkflowDefinitionDraftConnectionCommand}\"");
        Assert.IsFalse(xaml.Contains("Converter=", StringComparison.Ordinal));
    }

    private static string ReadSourceFile(params string[] pathParts)
    {
        var repoRoot = GetRepoRoot();
        return File.ReadAllText(Path.Combine(pathParts.Prepend(repoRoot).ToArray()));
    }

    private static string GetRepoRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI"))
                && Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI.Tests")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException("Could not locate FlowWeaver repository root.");
    }
}
